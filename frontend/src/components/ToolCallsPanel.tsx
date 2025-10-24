import React from "react";

type ToolCall =
  | { tool: "ioc_enrich"; ip: string; result: any }
  | { tool: "cve_lookup"; cve: string; result: any }
  | { tool: "log_query"; date: string; username?: string | null; result_count: number }
  | Record<string, any>;

interface Props {
  toolCalls?: ToolCall[];
  title?: string;
  maxHeight?: number; // px
}

/**
 * Renders a compact, scrollable summary of tool_calls beneath an assistant reply.
 * - Groups IOC enrichments, CVE lookups, and log queries into separate sections.
 * - Degrades gracefully if unexpected shapes are present.
 */
const ToolCallsPanel: React.FC<Props> = ({ toolCalls = [], title = "Enrichment", maxHeight = 260 }) => {
  if (!toolCalls.length) return null;

  const iocs = toolCalls.filter((t) => t.tool === "ioc_enrich") as Extract<ToolCall, { tool: "ioc_enrich" }>[];
  const cves = toolCalls.filter((t) => t.tool === "cve_lookup") as Extract<ToolCall, { tool: "cve_lookup" }>[];
  const logs = toolCalls.filter((t) => t.tool === "log_query") as Extract<ToolCall, { tool: "log_query" }>[];  

  const boxStyle: React.CSSProperties = {
    border: "1px solid rgba(255,255,255,0.12)",
    borderRadius: 12,
    padding: 12,
    marginTop: 12,
    background: "rgba(255,255,255,0.04)",
    maxHeight,
    overflow: "auto",
  };

  const sectionTitle: React.CSSProperties = {
    fontSize: 13,
    fontWeight: 600,
    opacity: 0.8,
    margin: "8px 0 6px",
  };

  const tableStyle: React.CSSProperties = {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: 13,
  };

  const thtd: React.CSSProperties = {
    borderBottom: "1px solid rgba(255,255,255,0.08)",
    padding: "6px 8px",
    textAlign: "left",
    verticalAlign: "top",
  };

  return (
    <div style={boxStyle}>
      <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>{title}</div>

      {!!iocs.length && (
        <>
          <div style={sectionTitle}>IP Reputation</div>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thtd}>IP</th>
                <th style={thtd}>Score</th>
                <th style={thtd}>Country</th>
                <th style={thtd}>ASN</th>
                <th style={thtd}>TOR</th>
                <th style={thtd}>Sources</th>
              </tr>
            </thead>
            <tbody>
              {iocs.map((c, i) => {
                const r = (c as any).result || {};
                return (
                  <tr key={`ioc-${i}`}>
                    <td style={thtd}>{r.ip || (c as any).ip}</td>
                    <td style={thtd}>{r.score ?? "—"}</td>
                    <td style={thtd}>{r.country ?? "—"}</td>
                    <td style={thtd}>{r.asn ?? "—"}</td>
                    <td style={thtd}>{String(r.is_tor ?? "—")}</td>
                    <td style={thtd}>{Array.isArray(r.sources) ? r.sources.join(", ") : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      {!!cves.length && (
        <>
          <div style={sectionTitle}>CVE Details</div>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thtd}>CVE</th>
                <th style={thtd}>Severity</th>
                <th style={thtd}>KEV</th>
                <th style={thtd}>Summary</th>
              </tr>
            </thead>
            <tbody>
              {cves.map((c, i) => {
                const r = (c as any).result || {};
                return (
                  <tr key={`cve-${i}`}>
                    <td style={thtd}>{r.cve || (c as any).cve}</td>
                    <td style={thtd}>{r.severity ?? "—"}</td>
                    <td style={thtd}>{r.kev ? "YES" : "no"}</td>
                    <td style={thtd}>{(r.summary || "—").slice(0, 240)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      {!!logs.length && (
        <>
          <div style={sectionTitle}>Log Query</div>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thtd}>Date</th>
                <th style={thtd}>Username</th>
                <th style={thtd}>Result Count</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l, i) => (
                <tr key={`log-${i}`}>
                  <td style={thtd}>{(l as any).date}</td>
                  <td style={thtd}>{(l as any).username || "—"}</td>
                  <td style={thtd}>{(l as any).result_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {!iocs.length && !cves.length && !logs.length && (
        <div style={{ fontSize: 13, opacity: 0.7 }}>No structured tool data returned.</div>
      )}
    </div>
  );
};

export default ToolCallsPanel;

