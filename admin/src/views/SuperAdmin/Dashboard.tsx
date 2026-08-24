import { useEffect, useState } from "react";
import { api, fmtNaira } from "../../api";
import { BarChart } from "../../components/BarChart";
import { Spinner } from "../../components/Spinner";

export function SuperDashboard() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { api.superDashboard().then(setData); }, []);
  if (!data) return <Spinner />;
  const days = (data.revenue_by_day || []).map((d: any) => ({ label: d.day, value: d.platform }));
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-head text-navy">Platform Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <Stat label="Active schools" value={String(data.schools_active)} />
        <Stat label="Gross revenue" value={fmtNaira(data.totals.gross)} />
        <Stat label="Platform earnings" value={fmtNaira(data.totals.platform)} />
        <Stat label="Orders" value={String(data.totals.count)} />
      </div>

      <div className="card">
        <h3 className="font-semibold text-navy mb-3">Platform earnings (last 30 days)</h3>
        <BarChart data={days} formatValue={fmtNaira} />
      </div>

      <div className="card">
        <h3 className="font-semibold text-navy mb-3">Revenue by school</h3>
        <table className="w-full text-sm">
          <thead className="text-xs uppercase text-gray-500">
            <tr><th className="text-left p-2">School</th><th className="text-right p-2">Orders</th><th className="text-right p-2">Gross</th><th className="text-right p-2">Platform</th><th className="text-right p-2">Admin</th></tr>
          </thead>
          <tbody>
            {(data.per_school || []).map((s: any) => (
              <tr key={s.school_id} className="border-t border-gray-100">
                <td className="p-2">{s.name}</td>
                <td className="p-2 text-right">{s.order_count}</td>
                <td className="p-2 text-right">{fmtNaira(s.gross)}</td>
                <td className="p-2 text-right text-emerald-700 font-semibold">{fmtNaira(s.platform)}</td>
                <td className="p-2 text-right">{fmtNaira(s.admin)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <div className="text-xs text-gray-500 uppercase">{label}</div>
      <div className="text-2xl font-head font-bold text-navy mt-1">{value}</div>
    </div>
  );
}
