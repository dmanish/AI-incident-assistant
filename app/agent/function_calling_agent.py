# app/agent/function_calling_agent.py
"""
True agentic system using LLM function calling APIs
Supports iterative reasoning and multi-turn tool execution
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple, Callable, Literal
from .tools import TOOL_DEFINITIONS, format_tool_result

LLMProvider = Literal["openai", "anthropic", "google"]


class FunctionCallingAgent:
    """
    Agent that uses LLM function calling to make decisions
    and execute tools iteratively. Tries OpenAI, Anthropic, then Google.
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
            model: Model to use (default: from env)
            max_iterations: Maximum number of agent loop iterations
            temperature: LLM temperature for responses
        """
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.tool_executors = tool_executors

        # Try to initialize with available provider
        self.client, self.provider = self._init_client()

        # Set model based on provider
        if model:
            self.model = model
        elif self.provider == "openai":
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        elif self.provider == "anthropic":
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        elif self.provider == "google":
            self.model = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
        else:
            self.model = "gpt-4o-mini"

    def _init_client(self) -> Tuple[Any, LLMProvider]:
        """Initialize LLM client. Try OpenAI, then Anthropic, then Google."""
        # Try OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                from openai import OpenAI
                return (OpenAI(api_key=openai_key), "openai")
            except Exception:
                pass

        # Try Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                import anthropic
                return (anthropic.Anthropic(api_key=anthropic_key), "anthropic")
            except Exception:
                pass

        # Try Google
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=google_key)
                return (genai, "google")
            except Exception:
                pass

        raise ValueError("No LLM API key found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY")

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
                if self.provider == "openai":
                    response = self._call_openai(messages)
                    assistant_content = response.choices[0].message.content
                    tool_calls = response.choices[0].message.tool_calls
                elif self.provider == "anthropic":
                    response = self._call_anthropic(messages)
                    assistant_content = next((c.text for c in response.content if hasattr(c, 'text')), None)
                    tool_calls = [c for c in response.content if hasattr(c, 'name')]
                elif self.provider == "google":
                    response = self._call_google(messages)
                    assistant_content = response.text if hasattr(response, 'text') else None
                    tool_calls = response.candidates[0].content.parts if hasattr(response.candidates[0].content, 'parts') else []
                    tool_calls = [p for p in tool_calls if hasattr(p, 'function_call')]
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
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

            # Normalize tool calls to common format
            normalized_tool_calls = self._normalize_tool_calls(tool_calls)

            # Add assistant's response to message history
            messages.append({
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": normalized_tool_calls
            })

            # Check if we have a final answer (no tool calls)
            if not normalized_tool_calls:
                final_answer = assistant_content or "I don't have enough information to answer."

                # Add final reasoning step
                reasoning_steps.append({
                    "step": iterations,
                    "type": "final_answer",
                    "description": "Agent synthesized final answer",
                    "llm_reasoning": assistant_content[:200] if assistant_content else None
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
            for tool_call in normalized_tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args_raw = tool_call["function"]["arguments"]

                # Parse arguments
                try:
                    tool_args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse tool arguments: {str(e)}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
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
                    "tool_call_id": tool_call["id"],
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

    def _call_openai(self, messages: List[Dict]) -> Any:
        """Call OpenAI API with function calling"""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=self.temperature,
            max_tokens=1000
        )

    def _call_anthropic(self, messages: List[Dict]) -> Any:
        """Call Anthropic API with tool use"""
        # Convert tools to Anthropic format
        tools = []
        for tool in TOOL_DEFINITIONS:
            tools.append({
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"]
            })

        # Extract system message
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [m for m in messages if m["role"] != "system"]

        return self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=system,
            messages=user_messages,
            tools=tools,
            temperature=self.temperature
        )

    def _call_google(self, messages: List[Dict]) -> Any:
        """Call Google Gemini API with function calling"""
        # Convert tools to Google format
        from google.ai.generativelanguage_v1beta.types import FunctionDeclaration, Tool

        tools_list = []
        for tool in TOOL_DEFINITIONS:
            tools_list.append(
                FunctionDeclaration(
                    name=tool["function"]["name"],
                    description=tool["function"]["description"],
                    parameters=tool["function"]["parameters"]
                )
            )

        # Create model with tools
        model = self.client.GenerativeModel(
            model_name=self.model,
            tools=[Tool(function_declarations=tools_list)]
        )

        # Combine messages into prompt
        prompt_parts = []
        for msg in messages:
            if msg["role"] == "user":
                prompt_parts.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                prompt_parts.append(f"Assistant: {msg['content']}")
            elif msg["role"] == "system":
                prompt_parts.insert(0, f"System: {msg['content']}")

        return model.generate_content("\n\n".join(prompt_parts))

    def _normalize_tool_calls(self, tool_calls: Any) -> List[Dict]:
        """Normalize tool calls from different providers to common format"""
        if not tool_calls:
            return []

        normalized = []

        if self.provider == "openai":
            for tc in tool_calls:
                normalized.append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })
        elif self.provider == "anthropic":
            for i, tc in enumerate(tool_calls):
                if hasattr(tc, 'name'):
                    normalized.append({
                        "id": f"tool_{i}",
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.input) if hasattr(tc, 'input') else "{}"
                        }
                    })
        elif self.provider == "google":
            for i, part in enumerate(tool_calls):
                if hasattr(part, 'function_call'):
                    fc = part.function_call
                    normalized.append({
                        "id": f"tool_{i}",
                        "type": "function",
                        "function": {
                            "name": fc.name,
                            "arguments": json.dumps(dict(fc.args)) if hasattr(fc, 'args') else "{}"
                        }
                    })

        return normalized

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
