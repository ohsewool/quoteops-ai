import { useCallback, useEffect, useState } from "react";

import { ApiClientError } from "../../app/api/client.js";
import { useAuth } from "../../app/auth/AuthProvider.jsx";
import { navigate } from "../../app/router.jsx";
import { advanceDemoRun, listDemoRuns, resetDemoRun, startDemoRun } from "./demoApi.js";

function demoErrorMessage(error) {
  if (error instanceof ApiClientError && error.code === "demo_unavailable") return "The guided demo is unavailable in this environment.";
  if (error instanceof ApiClientError && error.code === "permission_denied") return "Only an administrator can use the guided demo.";
  if (error instanceof ApiClientError && error.code === "stale_demo_run") return "The demo changed in another session. Refresh it before continuing.";
  return "The guided demo action could not be completed.";
}

export function DemoGuide() {
  const { request } = useAuth();
  const [run, setRun] = useState(null);
  const [state, setState] = useState("loading");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setState("loading");
    setMessage("");
    try {
      const page = await listDemoRuns(request);
      setRun(page.items[0] || null);
      setState("ready");
    } catch (error) {
      setState("error");
      setMessage(demoErrorMessage(error));
    }
  }, [request]);

  useEffect(() => {
    load();
  }, [load]);

  const start = async () => {
    setState("saving");
    setMessage("");
    try {
      setRun(await startDemoRun(request));
      setState("ready");
      setMessage("A two-product guided demo run is ready.");
    } catch (error) {
      setState("error");
      setMessage(demoErrorMessage(error));
    }
  };

  const advance = async () => {
    if (!run) return;
    setState("saving");
    try {
      setRun(await advanceDemoRun(request, run.id, run.version));
      setState("ready");
    } catch (error) {
      setState("error");
      setMessage(demoErrorMessage(error));
    }
  };

  const reset = async () => {
    if (!run) return;
    setState("saving");
    try {
      setRun(await resetDemoRun(request, run.id, run.version));
      setState("ready");
      setMessage("Guide state reset. Existing demo workflow records were not changed.");
    } catch (error) {
      setState("error");
      setMessage(demoErrorMessage(error));
    }
  };

  return (
    <section className="workspace-page demo-guide" aria-labelledby="demo-title">
      <p className="eyebrow">Explicit non-production demo</p>
      <h1 data-route-heading id="demo-title" tabIndex="-1">Guided demo</h1>
      <p className="page-lede">The guide starts only when an administrator asks for it. It creates no users or credentials and is unavailable outside an enabled non-production environment.</p>
      {state === "loading" ? <p className="inline-state" aria-live="polite">Loading demo state.</p> : null}
      {message ? <p className={state === "error" ? "form-error" : "inline-state"} role={state === "error" ? "alert" : undefined}>{message}</p> : null}
      {!run && state !== "loading" && state !== "error" ? <button className="button button-primary" disabled={state === "saving"} onClick={start} type="button">Start two-product demo</button> : null}
      {run ? (
        <section className="demo-guide-card" aria-labelledby="demo-run-title">
          <div className="pricing-section-heading"><div><h2 id="demo-run-title">Demo run #{run.id}</h2><p>Status: {run.status.replace("_", " ")}. Guide state is persisted separately from the workflow records.</p></div></div>
          {run.guide ? <div className="demo-guide-step"><p className="eyebrow">Step {run.guide.index + 1} of {run.guide.total_steps}</p><h3>{run.guide.title}</h3><p>{run.guide.description}</p><div className="request-form-actions"><button className="button button-secondary" onClick={() => navigate(run.guide.deep_link)} type="button">Open workspace</button><button className="button button-primary" disabled={state === "saving"} onClick={advance} type="button">Mark step complete</button></div></div> : <p className="inline-state">The guided demo is complete. The saved workflow artifacts remain available for review.</p>}
          <p className="read-only-note">MVP products: {(run.product_codes || []).join(", ")}</p>
          <dl className="status-list"><div><dt>Demo requests</dt><dd>{(run.artifacts.customer_request_ids || []).length}</dd></div><div><dt>Created source products</dt><dd>{(run.artifacts.created_product_ids || []).length}</dd></div><div><dt>Reused source products</dt><dd>{(run.artifacts.reused_product_ids || []).length}</dd></div></dl>
          <button className="button button-secondary" disabled={state === "saving"} onClick={reset} type="button">Reset guide state</button>
        </section>
      ) : null}
    </section>
  );
}
