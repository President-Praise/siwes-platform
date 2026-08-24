import { useEffect, useState } from "react";
import { api } from "../../api";
import { Spinner } from "../../components/Spinner";

export function SchoolSettings() {
  const [data, setData] = useState<any>(null);
  const [name, setName] = useState("");
  const [fullName, setFullName] = useState("");
  const [degrees, setDegrees] = useState("");
  const [departments, setDepartments] = useState("");
  const [colleges, setColleges] = useState("");
  const [submissionClause, setSubmissionClause] = useState("");
  const [awardClause, setAwardClause] = useState("");
  const [prices, setPrices] = useState<any>({});
  const [msg, setMsg] = useState("");

  async function load() {
    const d = await api.schoolSettings();
    setData(d);
    setName(d.school.name);
    setFullName(d.school.full_name);
    setDegrees(d.config.degrees || "[]");
    setDepartments(d.config.departments || "[]");
    setColleges(d.config.colleges || "[]");
    setSubmissionClause(d.config.submission_clause || "");
    setAwardClause(d.config.award_clause || "");
    setPrices(d.prices);
  }
  useEffect(() => { load(); }, []);
  if (!data) return <Spinner />;

  async function saveSettings() {
    setMsg("Saving…");
    try {
      // Validate JSON arrays
      JSON.parse(degrees); JSON.parse(departments); JSON.parse(colleges);
    } catch {
      setMsg("Degrees / departments / colleges must be valid JSON arrays."); return;
    }
    try {
      await api.schoolUpdateSettings({
        name, full_name: fullName,
        config: {
          degrees, departments, colleges,
          submission_clause: submissionClause, award_clause: awardClause,
        },
      });
      setMsg("Saved."); await load();
    } catch (e: any) { setMsg(e.message); }
  }

  async function savePrices() {
    setMsg("Saving prices…");
    try { await api.schoolUpdatePrices(prices); setMsg("Prices saved."); await load(); }
    catch (e: any) { setMsg(e.message); }
  }

  async function onLogo(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; if (!f) return;
    setMsg("Uploading…");
    try { await api.schoolUploadLogo(f); setMsg("Logo uploaded."); await load(); }
    catch (err: any) { setMsg(err.message); }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-head text-navy">Settings</h1>

      <div className="card space-y-3">
        <h3 className="font-semibold text-navy">University details</h3>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Display name</label><input className="input" value={name} onChange={e => setName(e.target.value)} /></div>
          <div><label className="label">Full name (used in documents)</label><input className="input" value={fullName} onChange={e => setFullName(e.target.value)} /></div>
        </div>
        <div className="flex items-center gap-3">
          <label className="btn btn-secondary cursor-pointer">
            Upload logo (PNG/JPG, ≤2MB)
            <input type="file" accept="image/png,image/jpeg" className="hidden" onChange={onLogo} />
          </label>
          {data.school.logo_path && <span className="text-xs text-gray-500">Current: {data.school.logo_path}</span>}
        </div>
      </div>

      <div className="card space-y-3">
        <h3 className="font-semibold text-navy">Academic options (offered on student form)</h3>
        <div>
          <label className="label">Degrees (JSON array)</label>
          <textarea className="input font-mono text-xs" rows={3} value={degrees} onChange={e => setDegrees(e.target.value)} />
          <p className="text-xs text-gray-500 mt-1">{`Example: [{"label": "B.Eng. Mechatronics Engineering", "short": "B.Eng."}]`}</p>
        </div>
        <div>
          <label className="label">Departments (JSON array of strings)</label>
          <textarea className="input font-mono text-xs" rows={3} value={departments} onChange={e => setDepartments(e.target.value)} />
        </div>
        <div>
          <label className="label">Colleges (JSON array of strings)</label>
          <textarea className="input font-mono text-xs" rows={2} value={colleges} onChange={e => setColleges(e.target.value)} />
        </div>
        <div>
          <label className="label">Submission clause template</label>
          <input className="input font-mono text-xs" value={submissionClause} onChange={e => setSubmissionClause(e.target.value)} />
          <p className="text-xs text-gray-500 mt-1">Placeholders: <code>{`{department}`}</code> <code>{`{college}`}</code> <code>{`{university_full_name}`}</code></p>
        </div>
        <div>
          <label className="label">Award clause template</label>
          <input className="input font-mono text-xs" value={awardClause} onChange={e => setAwardClause(e.target.value)} />
          <p className="text-xs text-gray-500 mt-1">Placeholders: <code>{`{degree}`}</code> <code>{`{degree_short}`}</code></p>
        </div>
      </div>

      <div className="card space-y-3">
        <h3 className="font-semibold text-navy">Pricing (₦)</h3>
        <div className="grid grid-cols-4 gap-3">
          {["basic", "standard", "premium", "express_addon"].map(p => (
            <div key={p}>
              <label className="label">{p}</label>
              <input className="input" type="number" value={prices[p]?.amount ?? 0} onChange={e => setPrices({...prices, [p]: { ...(prices[p] || {}), amount: parseInt(e.target.value || "0") }})} />
            </div>
          ))}
        </div>
        <button className="btn btn-primary" onClick={savePrices}>Save prices</button>
      </div>

      <div className="flex items-center gap-3">
        <button className="btn btn-primary" onClick={saveSettings}>Save settings</button>
        {msg && <span className="text-sm text-gray-600">{msg}</span>}
      </div>
    </div>
  );
}
