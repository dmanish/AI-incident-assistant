# app/agent/function_calling_agent.py
"""
True agentic system using OpenAI Function Calling API
Supports iterative reasoning and multi-turn tool execution
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple, Callable
from openai import OpenAI
from .tools import TOOL_DEFINITIONS, format_tool_result


class FunctionCallingAgent:
    """
    Agent that uses OpenAI's function calling to make decisions
    and execute tools iteratively
    """

    def __init__(
        self,
        tool_executors: Dict[str, Callable],
        model: str = None,
        max_iterations: int = 5,
        temperature: float = 0.2
    ):
        """
        Args:
            tool_executors: Dict mapping tool names to execution functions
            model: OpenAI model to use (default: from env or gpt-4o-mini)
            max_iterations: Maximum number of agent loop iterations
            temperature: LLM temperature for responses
        """
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.tool_executors = tool_executors

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set - function calling agent requires OpenAI")
        self.client = OpenAI(api_key=api_key)

    def run(
        self,
        user_message: str,
        role: str,
        conversation_history: List[Dict[str, str]] = None,
        audit_callback: Callable = None
    ) -> Dict[str, Any]:
        """
        Run the agent loop with iterative reasoning

        Args:
            user_message: User's query
            role: User's role (for RBAC)
            conversation_history: Previous messages in conversation
            audit_callback: Function to call for audit logging

        Returns:
            Dict with:
                - answer: Final answer from agent
                - tool_calls: List of tools called
                - iterations: Number of iterations used
                - messages: Full conversation history
                - reasoning_steps: Detailed steps taken by agent
                - routes_used: Which capabilities were used (LLM, RAG, tools)
        """
        # Initialize message history
        messages = conversation_history or []
        if not messages or messages[-1]["content"] != user_message:
            # Add system message if starting fresh
            if not any(m["role"] == "system" for m in messages):
                messages.insert(0, {
                    "role": "system",
                    "content": self._get_system_prompt()
                })
            messages.append({
                "role": "user",
                "content": user_message
            })

        tool_calls_made: List[Dict[str, Any]] = []
        reasoning_steps: List[Dict[str, Any]] = []
        routes_used = {
            "llm_calls": 0,
            "rag_searches": 0,
            "log_queries": 0,
            "tools_used": []
        }
        iterations = 0

        # Agent loop: iterate until final answer or max iterations
        for iteration in range(self.max_iterations):
            iterations = iteration + 1

            if audit_callback:
                audit_callback({
                    "action": "agent_iteration",
                    "iteration": iteration + 1,
                    "role": role
                })

            # Call LLM with tools available
            routes_used["llm_calls"] += 1

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",  # Let model decide
                    temperature=self.temperature,
                    max_tokens=1000
                )
            except Exception as e:
                if audit_callback:
                    audit_callback({
                        "action": "agent_llm_error",
                        "error": str(e),
                        "iteration": iteration + 1
                    })
                return {
                    "answer": f"Error calling LLM: {str(e)}",
                    "tool_calls": tool_calls_made,
                    "iterations": iterations,
                    "messages": messages,
                    "error": True
                }

            assistant_message = response.choices[0].message

            # Add assistant's response to message history
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in (assistant_message.tool_calls or [])
                ]
            })

            # Check if we have a final answer (no tool calls)
            if not assistant_message.tool_calls:
                final_answer = assistant_message.content or "I don't have enough information to answer."

                # Add final reasoning step
                reasoning_steps.append({
                    "step": iterations,
                    "type": "final_answer",
                    "description": "Agent synthesized final answer",
                    "llm_reasoning": assistant_message.content[:200] if assistant_message.content else None
                })

                if audit_callback:
                    audit_callback({
                        "action": "agent_complete",
                        "iterations": iterations,
                        "tool_calls_count": len(tool_calls_made)
                    })

                return {
                    "answer": final_answer,
                    "tool_calls": tool_calls_made,
                    "iterations": iterations,
                    "messages": messages,
                    "reasoning_steps": reasoning_steps,
                    "routes_used": routes_used,
                    "error": False
                }

            # Execute tool calls
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args_raw = tool_call.function.arguments

                # Parse arguments
                try:
                    tool_args = json.loads(tool_args_raw)
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse tool arguments: {str(e)}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": error_msg
                    })
                    continue

                # Track route usage
                if tool_name == "search_knowledge_base":
                    routes_used["rag_searches"] += 1
                elif tool_name == "query_failed_logins":
                    routes_used["log_queries"] += 1

                if tool_name not in routes_used["tools_used"]:
                    routes_used["tools_used"].append(tool_name)

                # Execute tool
                if audit_callback:
                    audit_callback({
                        "action": "agent_tool_call",
                        "tool": tool_name,
                        "arguments": tool_args,
                        "role": role,
                        "iteration": iteration + 1
                    })

                tool_result = self._execute_tool(
                    tool_name=tool_name,
                    arguments=tool_args,
                    role=role,
                    audit_callback=audit_callback
                )

                # Format result for LLM
                result_str = format_tool_result(
                    tool_name,
                    tool_result["result"],
                    success=tool_result["success"]
                )

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str
                })

                # Track tool call
                tool_calls_made.append({
                    "tool": tool_name,
                    "arguments": tool_args,
                    "success": tool_result["success"],
                    "result_summary": result_str[:200]  # First 200 chars
                })

                # Add reasoning step
                reasoning_steps.append({
                    "step": iterations,
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "description": self._get_tool_description(tool_name),
                    "arguments": tool_args,
                    "success": tool_result["success"],
                    "result_preview": result_str[:150]
                })

        # Max iterations reached
        if audit_callback:
            audit_callback({
                "action": "agent_max_iterations",
                "iterations": self.max_iterations,
                "tool_calls_count": len(tool_calls_made)
            })

        reasoning_steps.append({
            "step": iterations,
            "type": "max_iterations",
            "description": "Maximum iterations reached",
            "warning": True
        })

        return {
            "answer": "I've gathered information but need more iterations to provide a complete answer. Please try rephrasing your question or breaking it into smaller parts.",
            "tool_calls": tool_calls_made,
            "iterations": iterations,
            "messages": messages,
            "reasoning_steps": reasoning_steps,
            "routes_used": routes_used,
            "error": False,
            "max_iterations_reached": True
        }

    def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        role: str,
        audit_callback: Callable = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with RBAC checks

        Returns:
            Dict with:
                - success: bool
                - result: Tool result or error message
        """
        if tool_name not in self.tool_executors:
            return {
                "success": False,
                "result": f"Tool '{tool_name}' not found"
            }

        executor = self.tool_executors[tool_name]

        try:
            # Execute tool (executor should handle RBAC)
            result = executor(arguments=arguments, role=role)
            return {
                "success": True,
                "result": result
            }
        except PermissionError as e:
            # RBAC violation
            if audit_callback:
                audit_callback({
                    "action": "tool_rbac_violation",
                    "tool": tool_name,
                    "role": role,
                    "error": str(e)
                })
            return {
                "success": False,
                "result": f"Permission denied: {str(e)}"
            }
        except Exception as e:
            # Tool execution error
            if audit_callback:
                audit_callback({
                    "action": "tool_execution_error",
                    "tool": tool_name,
                    "role": role,
                    "error": str(e)
                })
            return {
                "success": False,
                "result": f"Error executing tool: {str(e)}"
            }

    def _get_tool_description(self, tool_name: str) -> str:
        """Get human-readable description of what a tool does"""
        descriptions = {
            "search_knowledge_base": "Searched security policies and playbooks",
            "query_failed_logins": "Queried authentication logs for failed login attempts"
        }
        return descriptions.get(tool_name, f"Used tool: {tool_name}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return """You are an enterprise security incident assistant with access to specialized tools.

Your role:
- Help security and engineering teams respond to incidents
- Search security policies, playbooks, and procedures
- Query authentication logs and analyze patterns
- Provide actionable, step-by-step guidance

Available tools:
1. search_knowledge_base: Search security policies and playbooks
2. query_failed_logins: Search authentication logs for failed login attempts

Guidelines:
- Use tools when needed to gather accurate information
- You can call multiple tools in sequence to gather complete information
- Be concise and actionable in your responses
- If you don't have enough information, ask the user for clarification
- Always cite sources when using policy/playbook information
- When analyzing logs, look for patterns (IPs, timing, users)

Remember: You're helping with real security incidents. Accuracy and clarity are critical."""


def create_agent(tool_executors: Dict[str, Callable]) -> FunctionCallingAgent:
    """
    Factory function to create a configured agent

    Args:
        tool_executors: Dict mapping tool names to execution functions

    Returns:
        Configured FunctionCallingAgent
    """
    return FunctionCallingAgent(
        tool_executors=tool_executors,
        max_iterations=5,
        temperature=0.2
    )
