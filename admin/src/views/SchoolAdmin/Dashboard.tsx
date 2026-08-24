import { useEffect, useState } from "react";
import { api, fmtNaira } from "../../api";
import { BarChart } from "../../components/BarChart";
import { OrdersTable } from "../../components/OrdersTable";
import { Spinner } from "../../components/Spinner";

export function SchoolDashboard() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { api.schoolDashboard().then(setData); }, []);
  if (!data) return <Spinner />;
  const days = (data.by_day || []).map((d: any) => ({ label: d.day, value: d.revenue }));
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-head text-navy">{data.school.name} Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <Stat label="Orders" value={String(data.revenue.count)} />
        <Stat label="Gross revenue" value={fmtNaira(data.revenue.gross)} />
        <Stat label="Your share" value={fmtNaira(data.revenue.admin)} />
        <Stat label="Platform fee" value={fmtNaira(data.revenue.platform)} />
      </div>
      <div className="card">
        <h3 className="font-semibold text-navy mb-3">Revenue last 30 days</h3>
        <BarChart data={days} formatValue={fmtNaira} />
      </div>
      <div className="card">
        <h3 className="font-semibold text-navy mb-3">Recent orders</h3>
        <OrdersTable orders={data.recent} />
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
