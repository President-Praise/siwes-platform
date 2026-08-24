import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type School } from "../../api";
import { Spinner } from "../../components/Spinner";

export function SuperSchools() {
  const [schools, setSchools] = useState<School[] | null>(null);
  const [showNew, setShowNew] = useState(false);

  async function load() { setSchools(await api.superListSchools()); }
  useEffect(() => { load(); }, []);
  if (!schools) return <Spinner />;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-head text-navy">Schools</h1>
        <button className="btn btn-primary" onClick={() => setShowNew(true)}>+ Add school</button>
      </div>
      <div className="card">
        <table className="w-full text-sm">
          <thead className="text-xs uppercase text-gray-500">
            <tr><th className="text-left p-2">Slug</th><th className="text-left p-2">Name</th><th className="text-right p-2">Cut %</th><th className="text-left p-2">Active</th><th></th></tr>
          </thead>
          <tbody>
            {schools.map(s => (
              <tr key={s.id} className="border-t border-gray-100">
                <td className="p-2 font-mono text-xs">/{s.slug}</td>
                <td className="p-2">{s.name}</td>
                <td className="p-2 text-right">{s.platform_cut_pct}%</td>
                <td className="p-2">{s.active ? "Active" : "Inactive"}</td>
                <td className="p-2"><Link to={`/schools/${s.id}`} className="text-navy underline">Manage</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showNew && <NewSchoolModal onClose={() => setShowNew(false)} onCreated={load} />}
    </div>
  );
}

function NewSchoolModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    slug: "", name: "", full_name: "", referral_prefix: "",
    platform_cut_pct: 20, paystack_secret_key: "", paystack_public_key: "",
  });
  const [err, setErr] = useState("");
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr("");
    try {
      await api.superCreateSchool(form);
      onCreated(); onClose();
    } catch (e: any) { setErr(e.message); }
  }
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <form className="card w-full max-w-lg space-y-3" onSubmit={submit}>
        <h2 className="text-xl font-head text-navy">New school</h2>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Slug (URL)</label><input className="input" value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value })} placeholder="lmu" required /></div>
          <div><label className="label">Referral prefix</label><input className="input" value={form.referral_prefix} onChange={e => setForm({ ...form, referral_prefix: e.target.value })} placeholder="LMU" required /></div>
        </div>
        <div><label className="label">Name</label><input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Landmark University" required /></div>
        <div><label className="label">Full name (for documents)</label><input className="input" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} placeholder="Landmark University, Omu-Aran" required /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Platform cut (%)</label><input className="input" type="number" min={0} max={100} value={form.platform_cut_pct} onChange={e => setForm({ ...form, platform_cut_pct: parseInt(e.target.value || "0") })} /></div>
          <div><label className="label">Paystack public key</label><input className="input" value={form.paystack_public_key} onChange={e => setForm({ ...form, paystack_public_key: e.target.value })} /></div>
        </div>
        <div><label className="label">Paystack secret key</label><input className="input" value={form.paystack_secret_key} onChange={e => setForm({ ...form, paystack_secret_key: e.target.value })} placeholder="sk_test_..." /></div>
        {err && <div className="text-red-600 text-sm">{err}</div>}
        <div className="flex gap-2 justify-end">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary">Create</button>
        </div>
      </form>
    </div>
  );
}
