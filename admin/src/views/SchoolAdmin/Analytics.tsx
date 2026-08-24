import { useEffect, useState } from "react";
import { api, fmtNaira } from "../../api";
import { BarChart } from "../../components/BarChart";
import { Spinner } from "../../components/Spinner";

export function SchoolAnalytics() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { api.schoolAnalytics(30).then(setData); }, []);
  if (!data) return <Spinner />;
  const days = (data.by_day || []).map((d: any) => ({ label: d.day, value: d.revenue }));
  const orders = (data.by_day || []).map((d: any) => ({ label: d.day, value: d.orders }));
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-head text-navy">Analytics</h1>
      <div className="grid grid-cols-4 gap-3">
        <Stat label="Total orders" value={String(data.revenue.count)} />
        <Stat label="Gross" value={fmtNaira(data.revenue.gross)} />
        <Stat label="Your share" value={fmtNaira(data.revenue.admin)} />
        <Stat label="Platform fee" value={fmtNaira(data.revenue.platform)} />
      </div>
      <div className="card">
        <h3 className="font-semibold text-navy mb-2">Revenue (30 days)</h3>
        <BarChart data={days} formatValue={fmtNaira} />
      </div>
      <div className="card">
        <h3 className="font-semibold text-navy mb-2">Orders per day</h3>
        <BarChart data={orders} />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="card"><div className="text-xs text-gray-500 uppercase">{label}</div><div className="text-2xl font-head font-bold text-navy mt-1">{value}</div></div>;
}
