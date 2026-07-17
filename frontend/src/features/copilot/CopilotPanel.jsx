import { useState } from "react";

import { ApiClientError } from "../../app/api/client.js";
import { useAuth } from "../../app/auth/AuthProvider.jsx";
import { createCopilotOutput } from "./copilotApi.js";

function canManage(role) {
  return role === "admin" || role === "manager";
}

function errorMessage(error) {
  if (error instanceof ApiClientError && error.code === "permission_denied") {
    return "You do not have permission to generate this grounded draft.";
  }
  if (error instanceof ApiClientError && error.code === "network_unavailable") {
    return "The grounded draft service is unavailable. Try again after connectivity is restored.";
  }
  return "The grounded draft could not be generated. The saved pricing and workflow evidence was not changed.";
}

function outputModeLabel(output) {
  return output.deterministic_fallback ? "Deterministic fallback" : "Grounded provider output";
}

export function CopilotPanel({ actions, quoteId, title = "Grounded Copilot" }) {
  const { request, user } = useAuth();
  const [state, setState] = useState({ busyActionId: null, error: "", output: null });
  const manager = canManage(user?.role);

  if (!actions?.length || !quoteId) return null;

  const generate = async (action) => {
    setState({ busyActionId: action.id, error: "", output: null });
    try {
      const output = await createCopilotOutput(request, quoteId, action.payload);
      setState({ busyActionId: null, error: "", output });
    } catch (error) {
      setState({ busyActionId: null, error: errorMessage(error), output: null });
    }
  };

  return (
    <section className="copilot-panel" aria-labelledby={`copilot-panel-${quoteId}`}>
      <div className="copilot-panel-heading">
        <div>
          <p className="eyebrow">Read-only grounded assistance</p>
          <h2 id={`copilot-panel-${quoteId}`}>{title}</h2>
          <p>Generated text is saved with source artifacts. It cannot change prices, validations, approvals, reports, or workflow state.</p>
        </div>
      </div>
      {manager ? (
        <div className="copilot-actions">
          {actions.map((action) => (
            <button
              className="button button-secondary"
              disabled={Boolean(state.busyActionId)}
              key={action.id}
              onClick={() => generate(action)}
              type="button"
            >
              {state.busyActionId === action.id ? "Generating grounded draft..." : action.label}
            </button>
          ))}
        </div>
      ) : <p className="read-only-note">Viewer access can read saved evidence but cannot request a new grounded draft.</p>}
      {state.error ? <p className="form-error" role="alert">{state.error}</p> : null}
      {state.output ? (
        <article className="copilot-output" aria-live="polite">
          <div className="copilot-output-heading">
            <strong>{outputModeLabel(state.output)}</strong>
            <span>{state.output.provider_name}</span>
          </div>
          <p>{state.output.generated_text}</p>
          <details>
            <summary>Grounding evidence</summary>
            <ul>
              {state.output.source_artifacts.map((artifact) => (
                <li key={`${artifact.artifact_type}-${artifact.artifact_id}`}>{artifact.artifact_type} #{artifact.artifact_id}</li>
              ))}
            </ul>
            {state.output.triggered_rules.length ? (
              <ul>
                {state.output.triggered_rules.map((rule) => <li key={rule.code}>{rule.code}: {rule.passed ? "passed" : "review required"}</li>)}
              </ul>
            ) : null}
          </details>
        </article>
      ) : null}
    </section>
  );
}
