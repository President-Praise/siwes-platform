import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, fmtNaira } from "../../api";
import { Spinner } from "../../components/Spinner";

export function SuperSchoolDetail() {
  const { id } = useParams();
  const sid = Number(id);
  const [data, setData] = useState<any>(null);
  const [editFields, setEditFields] = useState<any>({});
  const [msg, setMsg] = useState("");

  async function load() {
    const d = await api.superGetSchool(sid);
    setData(d);
    setEditFields({
      name: d.school.name, full_name: d.school.full_name, slug: d.school.slug,
      referral_prefix: d.school.referral_prefix, platform_cut_pct: d.school.platform_cut_pct,
      paystack_secret_key: d.school.paystack_secret_key || "",
      paystack_public_key: d.school.paystack_public_key || "",
      active: !!d.school.active,
    });
  }
  useEffect(() => { load(); }, [sid]);
  if (!data) return <Spinner />;

  async function save() {
    setMsg("Saving…");
    try { await api.superUpdateSchool(sid, editFields); setMsg("Saved."); await load(); }
    catch (e: any) { setMsg(e.message); }
  }

  async function onLogo(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; if (!f) return;
    setMsg("Uploading…");
    try { await api.superUploadLogo(sid, f); setMsg("Logo uploaded."); await load(); }
    catch (err: any) { setMsg(err.message); }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-head text-navy">{data.school.name}</h1>
      <p className="text-sm text-gray-500"><code>/{data.school.slug}</code> · {data.school.full_name}</p>

      <div className="card">
        <h3 className="font-semibold mb-3 text-navy">Revenue</h3>
        <div className="grid grid-cols-4 gap-3 text-sm">
          <Stat label="Orders" value={String(data.revenue.count)} />
          <Stat label="Gross" value={fmtNaira(data.revenue.gross)} />
          <Stat label="Platform" value={fmtNaira(data.revenue.platform)} />
          <Stat label="Admin" value={fmtNaira(data.revenue.admin)} />
        </div>
      </div>

      <div className="card space-y-3">
        <h3 className="font-semibold text-navy">School details</h3>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Slug</label><input className="input" value={editFields.slug} onChange={e => setEditFields({...editFields, slug: e.target.value})} /></div>
          <div><label className="label">Referral prefix</label><input className="input" value={editFields.referral_prefix} onChange={e => setEditFields({...editFields, referral_prefix: e.target.value})} /></div>
          <div><label className="label">Name</label><input className="input" value={editFields.name} onChange={e => setEditFields({...editFields, name: e.target.value})} /></div>
          <div><label className="label">Full name</label><input className="input" value={editFields.full_name} onChange={e => setEditFields({...editFields, full_name: e.target.value})} /></div>
          <div><label className="label">Platform cut %</label><input className="input" type="number" value={editFields.platform_cut_pct} onChange={e => setEditFields({...editFields, platform_cut_pct: parseInt(e.target.value || "0")})} /></div>
          <div><label className="label">Active</label><select className="input" value={editFields.active ? "1" : "0"} onChange={e => setEditFields({...editFields, active: e.target.value === "1"})}><option value="1">Active</option><option value="0">Inactive</option></select></div>
          <div><label className="label">Paystack public key</label><input className="input" value={editFields.paystack_public_key} onChange={e => setEditFields({...editFields, paystack_public_key: e.target.value})} /></div>
          <div><label className="label">Paystack secret key</label><input className="input" value={editFields.paystack_secret_key} onChange={e => setEditFields({...editFields, paystack_secret_key: e.target.value})} /></div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-primary" onClick={save}>Save</button>
          <label className="btn btn-secondary cursor-pointer">
            Upload logo
            <input type="file" accept="image/png,image/jpeg" className="hidden" onChange={onLogo} />
          </label>
          {data.school.logo_path && <span className="text-xs text-gray-500">Current: {data.school.logo_path}</span>}
          {msg && <span className="text-sm text-gray-600">{msg}</span>}
        </div>
      </div>

      <div className="card">
        <h3 className="font-semibold text-navy mb-2">School admins</h3>
        <SchoolAdminsList schoolId={sid} admins={data.admins} reload={load} />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="bg-gray-50 rounded p-3"><div className="text-xs text-gray-500 uppercase">{label}</div><div className="text-lg font-semibold text-navy">{value}</div></div>;
}

function SchoolAdminsList({ schoolId, admins, reload }: { schoolId: number; admins: any[]; reload: () => void }) {
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ username: "", pin: "", display_name: "" });
  const [err, setErr] = useState("");

  async function create() {
    setErr("");
    try {
      await api.superCreateAdmin(schoolId, form);
      setShowNew(false); setForm({ username: "", pin: "", display_name: "" }); reload();
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <div>
      <button className="btn btn-secondary text-sm mb-3" onClick={() => setShowNew(!showNew)}>{showNew ? "Cancel" : "+ Add admin"}</button>
      {showNew && (
        <div className="bg-gray-50 p-3 rounded mb-3 space-y-2">
          <div className="grid grid-cols-3 gap-2">
            <input className="input" placeholder="username" value={form.username} onChange={e => setForm({...form, username: e.target.value})} />
            <input className="input" placeholder="PIN" value={form.pin} onChange={e => setForm({...form, pin: e.target.value})} />
            <input className="input" placeholder="Display name" value={form.display_name} onChange={e => setForm({...form, display_name: e.target.value})} />
          </div>
          {err && <div className="text-sm text-red-600">{err}</div>}
          <button className="btn btn-primary text-sm" onClick={create}>Create</button>
        </div>
      )}
      <table className="w-full text-sm">
        <thead className="text-xs uppercase text-gray-500"><tr><th className="text-left p-2">Username</th><th className="text-left p-2">Name</th><th className="text-left p-2">Active</th><th></th></tr></thead>
        <tbody>
          {admins.map(a => (
            <tr key={a.id} className="border-t border-gray-100">
              <td className="p-2 font-mono text-xs">{a.username}</td>
              <td className="p-2">{a.display_name || "—"}</td>
              <td className="p-2">{a.active ? "Active" : "Disabled"}</td>
              <td className="p-2">
                <ResetPinButton adminId={a.id} reload={reload} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResetPinButton({ adminId, reload }: { adminId: number; reload: () => void }) {
  const [pin, setPin] = useState("");
  const [show, setShow] = useState(false);
  async function reset() {
    if (pin.length < 4) return;
    await api.superUpdateAdmin(adminId, { pin });
    setShow(false); setPin(""); reload();
  }
  if (!show) return <button className="text-xs text-navy underline" onClick={() => setShow(true)}>Reset PIN</button>;
  return (
    <div className="flex gap-1">
      <input className="input text-xs w-24" placeholder="new PIN" value={pin} onChange={e => setPin(e.target.value)} />
      <button className="btn btn-primary text-xs px-2 py-1" onClick={reset}>Set</button>
    </div>
  );
}
