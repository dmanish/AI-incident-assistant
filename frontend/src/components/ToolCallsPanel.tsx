import React from "react";

type IocCall = { tool: "ioc_enrich"; ip: string; result: any };
type CveLookupCall = { tool: "cve_lookup"; cve: string; result: any };
type CveSearchResult = { cve: string; severity?: string; summary?: string; published?: string };
type CveSearchCall = { tool: "cve_search"; keyword: string; results: CveSearchResult[] };
type LogCall = { tool: "log_query"; date: string; username?: string | null; result_count: number };

export type ToolCall = IocCall | CveLookupCall | CveSearchCall | LogCall | Record<string, any>;

interface Props {
  toolCalls?: ToolCall[];
  title?: string;
  maxHeight?: number; // px
}

/**
 * ToolCallsPanel
 * --------------
 * Renders a compact, scrollable summary of `tool_calls` for an assistant message.
 * Sections:
 *  - IP Reputation (IOC enrichment)
 *  - CVE Details (single-ID lookups)
 *  - CVE Search (web results, keyword or "today")
 *  - Log Query (failed login summary)
 *
 * Usage:
 *   <ToolCallsPanel toolCalls={message.tool_calls} />
 */
const ToolCallsPanel: React.FC<Props> = ({ toolCalls = [], title = "Enrichment", maxHeight = 260 }) => {
  if (!toolCalls.length) return null;

  const iocs = toolCalls.filter((t) => t.tool === "ioc_enrich") as IocCall[];
  const cves = toolCalls.filter((t) => t.tool === "cve_lookup") as CveLookupCall[];
  const cveSearches = toolCalls.filter((t) => t.tool === "cve_search") as CveSearchCall[];
  const logs = toolCalls.filter((t) => t.tool === "log_query") as LogCall[];

  const boxStyle: React.CSSProperties = {
    border: "1px solid rgba(127,127,127,0.25)",
    borderRadius: 12,
    padding: 12,
    marginTop: 12,
    background: "rgba(127,127,127,0.08)",
    maxHeight,
    overflow: "auto",
  };

  const titleStyle: React.CSSProperties = {
    fontSize: 14,
    fontWeight: 700,
    marginBottom: 6,
  };

  const sectionTitle: React.CSSProperties = {
    fontSize: 13,
    fontWeight: 600,
    opacity: 0.85,
    margin: "10px 0 6px",
  };

  const tableStyle: React.CSSProperties = {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: 13,
  };

  const thtd: React.CSSProperties = {
    borderBottom: "1px solid rgba(127,127,127,0.25)",
    padding: "6px 8px",
    textAlign: "left",
    verticalAlign: "top",
  };

  return (
    <div style={boxStyle} aria-label="Tool call enrichment">
      <div style={titleStyle}>{title}</div>

      {/* IOC Enrichment */}
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
                const r = c.result || {};
                return (
                  <tr key={`ioc-${i}`}>
                    <td style={thtd}>{r.ip ?? c.ip}</td>
                    <td style={thtd}>{r.score ?? "—"}</td>
                    <td style={thtd}>{r.country ?? "—"}</td>
                    <td style={thtd}>{r.asn ?? "—"}</td>
                    <td style={thtd}>{r.is_tor === true ? "true" : r.is_tor === false ? "false" : "—"}</td>
                    <td style={thtd}>{Array.isArray(r.sources) ? r.sources.join(", ") : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      {/* CVE Lookup (single IDs) */}
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
                const r = c.result || {};
                return (
                  <tr key={`cve-${i}`}>
                    <td style={thtd}>{r.cve ?? c.cve}</td>
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

      {/* CVE Search (web, keyword/"today") */}
      {!!cveSearches.length && (
        <>
          <div style={sectionTitle}>CVE Search (web)</div>
          {cveSearches.map((s, i) => (
            <div key={`cves-${i}`} style={{ marginBottom: 10 }}>
              <div style={{ opacity: 0.8, fontSize: 12, margin: "2px 0 6px" }}>
                Keyword: <b>{s.keyword || "—"}</b> · {(s.results || []).length} results
              </div>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thtd}>CVE</th>
                    <th style={thtd}>Severity</th>
                    <th style={thtd}>Published</th>
                    <th style={thtd}>Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {(s.results || []).map((r, j) => (
                    <tr key={`cves-${i}-${j}`}>
                      <td style={thtd}>{r.cve}</td>
                      <td style={thtd}>{r.severity ?? "—"}</td>
                      <td style={thtd}>{r.published ?? "—"}</td>
                      <td style={thtd}>{(r.summary || "—").slice(0, 240)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </>
      )}

      {/* Log Query */}
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
                  <td style={thtd}>{l.date}</td>
                  <td style={thtd}>{l.username || "—"}</td>
                  <td style={thtd}>{l.result_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* Fallback if an unexpected tool type arrives */}
      {!iocs.length && !cves.length && !cveSearches.length && !logs.length && (
        <div style={{ fontSize: 13, opacity: 0.7 }}>No structured tool data returned.</div>
      )}
    </div>
  );
};

export default ToolCallsPanel;

