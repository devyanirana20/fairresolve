import { useEffect, useState, useCallback } from "react";
import { api } from "./api";

const TIER_LABEL = {
  tier_1_deterministic: "Tier 1 \u2014 Deterministic",
  tier_2_fairness_narrative: "Tier 2 \u2014 Fairness-narrative",
};

const STATUS_BADGE = {
  filed: { label: "Filed", cls: "badge-pending" },
  evidence_collected: { label: "Processing", cls: "badge-pending" },
  tier_routed: { label: "Processing", cls: "badge-pending" },
  weighed: { label: "Processing", cls: "badge-pending" },
  auto_resolved_card_member: { label: "Resolved", cls: "badge-resolved" },
  auto_resolved_merchant: { label: "Resolved", cls: "badge-resolved" },
  flagged_for_review: { label: "Flagged", cls: "badge-review" },
  human_reviewed: { label: "Reviewed", cls: "badge-review" },
  appealed: { label: "Appealed", cls: "badge-appealed" },
};

function StatusBadge({ status }) {
  const meta = STATUS_BADGE[status] || { label: status, cls: "badge-pending" };
  return <span className={`badge ${meta.cls}`}>{meta.label}</span>;
}

function ConfidenceBar({ score }) {
  if (score === null || score === undefined) return null;
  const color = score >= 70 ? "var(--green)" : score >= 30 ? "var(--gold)" : "var(--coral)";
  return (
    <div className="confidence-row">
      <div className="confidence-bar">
        <div className="confidence-fill" style={{ width: `${score}%`, background: color }} />
      </div>
      <div className="confidence-label">{score}% confidence</div>
    </div>
  );
}

function NewDisputeModal({ reasonCodes, transactions, onClose, onFiled }) {
  const [transactionId, setTransactionId] = useState(transactions[0]?.id || "");
  const [reasonCode, setReasonCode] = useState(reasonCodes[0]?.code || "");
  const [statement, setStatement] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const selectedCode = reasonCodes.find((rc) => rc.code === reasonCode);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const dispute = await api.fileDispute({
        transaction_id: transactionId,
        reason_code: reasonCode,
        card_member_statement: statement,
      });
      onFiled(dispute);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <h2>File a new dispute</h2>
        <div className="sub">Runs through the real pipeline - evidence collection, tier routing, and (for Tier 2 codes) the trained weighing model.</div>

        <div className="field">
          <label>Transaction to dispute</label>
          <select value={transactionId} onChange={(e) => setTransactionId(e.target.value)}>
            {transactions.map((t) => (
              <option key={t.id} value={t.id}>
                {t.merchant_name} - ${t.amount.toFixed(2)}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Reason code</label>
          <select value={reasonCode} onChange={(e) => setReasonCode(e.target.value)}>
            {reasonCodes.map((rc) => (
              <option key={rc.code} value={rc.code}>
                {rc.code} - {rc.name}
              </option>
            ))}
          </select>
        </div>

        {selectedCode && (
          <div className="tier-hint">
            {selectedCode.always_human
              ? "This reason code never auto-resolves by design \u2014 legal interpretation always routes straight to a human reviewer."
              : selectedCode.tier === "tier_1_deterministic"
              ? "Tier 1 \u2014 deterministic. Resolves almost instantly on a direct record match."
              : "Tier 2 \u2014 fairness-narrative. Goes through the credibility engine and the trained weighing model."}
          </div>
        )}

        <div className="field">
          <label>What happened?</label>
          <textarea
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            placeholder="Briefly describe the issue..."
          />
        </div>

        {error && <div className="error-text">{error}</div>}

        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting || !transactionId}>
            {submitting ? "Processing\u2026" : "Submit dispute"}
          </button>
        </div>
      </div>
    </div>
  );
}

function DisputeDetail({ dispute, onAppeal, appealing }) {
  const [viewAs, setViewAs] = useState("cm");
  if (!dispute) {
    return (
      <div className="empty">
        <h2>Select a case</h2>
        <p>Choose a case from the sidebar, or file a new dispute to run it through the real pipeline live.</p>
      </div>
    );
  }

  const resolved = ["auto_resolved_card_member", "auto_resolved_merchant"].includes(dispute.status);
  const canAppeal = resolved && !dispute.appeal_requested;

  return (
    <div>
      <div className="case-header">
        <div>
          <h1>{dispute.reason_code_name}</h1>
          <div className="meta">
            <b>{dispute.reason_code}</b> &middot; Filed {new Date(dispute.filed_at).toLocaleString()}
          </div>
        </div>
        <StatusBadge status={dispute.status} />
      </div>

      <div className="view-toggle">
        <button className={viewAs === "cm" ? "active" : ""} onClick={() => setViewAs("cm")}>Card member view</button>
        <button className={viewAs === "merchant" ? "active" : ""} onClick={() => setViewAs("merchant")}>Merchant view</button>
      </div>

      <div className="card">
        <h3>{TIER_LABEL[dispute.tier] || "Routing\u2026"}</h3>
        {viewAs === "merchant" && (
          <div className="viewer-note">Viewing exactly what the merchant sees - same reasoning, same evidence, same confidence score.</div>
        )}
        <p className="reasoning-text">{dispute.reasoning_text}</p>
        <ConfidenceBar score={dispute.confidence_score} />
      </div>

      {dispute.feature_attributions && (
        <div className="card">
          <h3>What the model weighed (Captum attributions)</h3>
          <div className="attr-list">
            {dispute.feature_attributions
              .filter((a) => !a.feature.startsWith("code_"))
              .map((a) => (
                <div className="attr-row" key={a.feature}>
                  <span className="attr-name">{a.feature.replaceAll("_", " ")}</span>
                  <span className={`attr-bar ${a.attribution >= 0 ? "pos" : "neg"}`}
                        style={{ width: `${Math.min(Math.abs(a.attribution) * 200, 100)}%` }} />
                  <span className="attr-value">{a.attribution.toFixed(3)}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      <div className="card">
        <h3>SLA tracking</h3>
        <div className="sla-strip">
          <span><b>{dispute.sla.days_remaining_on_issuer_clock} days</b> remaining &middot; issuer clock (FCBA/Reg Z)</span>
          <span><b>Merchant challenge by</b> {new Date(dispute.sla.merchant_challenge_by).toLocaleDateString()}</span>
          {dispute.sla.issuer_deadline_at_risk && <span className="sla-risk">{"\u26a0 Deadline at risk"}</span>}
        </div>
      </div>

      <div className="actions-row">
        {canAppeal && (
          <button className="btn btn-amber" onClick={() => onAppeal(dispute.id)} disabled={appealing}>
            {appealing ? "Routing\u2026" : "One-tap appeal"}
          </button>
        )}
        {dispute.appeal_requested && <span className="appealed-note">Appeal routed to a human reviewer.</span>}
      </div>
    </div>
  );
}

export default function App() {
  const [disputes, setDisputes] = useState([]);
  const [reasonCodes, setReasonCodes] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [appealing, setAppealing] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [d, rc, tx] = await Promise.all([
        api.listDisputes(),
        api.listReasonCodes(),
        fetch((import.meta.env.VITE_API_BASE || "http://localhost:8000") + "/api/transactions").then((r) => r.json()),
      ]);
      setDisputes(d);
      setReasonCodes(rc);
      setTransactions(tx.filter((t) => !t.was_disputed));
      setActiveId((prev) => prev || (d.length > 0 ? d[0].id : null));
    } catch (e) {
      setLoadError(e.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const active = disputes.find((d) => d.id === activeId);

  async function handleAppeal(id) {
    setAppealing(true);
    try {
      const updated = await api.appealDispute(id);
      setDisputes((prev) => prev.map((d) => (d.id === id ? updated : d)));
    } catch (e) {
      alert(e.message);
    } finally {
      setAppealing(false);
    }
  }

  function handleFiled(dispute) {
    setDisputes((prev) => [dispute, ...prev]);
    setActiveId(dispute.id);
    setShowModal(false);
    refresh();
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="#1E2761" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3v18M5 8l-3 6a4 4 0 0 0 8 0l-3-6M19 8l-3 6a4 4 0 0 0 8 0l-3-6M4 8h4M16 8h4" />
            </svg>
          </span>
          <span className="name">FairResolve</span>
        </div>

        <button className="new-btn" onClick={() => setShowModal(true)}>
          + File a new dispute
        </button>

        <div className="side-label">Cases</div>
        <div className="case-list">
          {loadError && <div className="error-text">Couldn't reach the API: {loadError}</div>}
          {disputes.map((d) => (
            <div
              key={d.id}
              className={`case-item ${d.id === activeId ? "active" : ""}`}
              onClick={() => setActiveId(d.id)}
            >
              <div className="row1">
                <span className="id">{d.reason_code}</span>
              </div>
              <div className="merchant">{d.reason_code_name}</div>
              <StatusBadge status={d.status} />
            </div>
          ))}
        </div>

        <div className="sidebar-foot">FairResolve \u2014 real backend, real model</div>
      </aside>

      <main className="main">
        <DisputeDetail dispute={active} onAppeal={handleAppeal} appealing={appealing} />
      </main>

      {showModal && (
        <NewDisputeModal
          reasonCodes={reasonCodes}
          transactions={transactions}
          onClose={() => setShowModal(false)}
          onFiled={handleFiled}
        />
      )}
    </div>
  );
}
