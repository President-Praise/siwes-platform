import { useEffect, useState } from "react";
import { api, type Order } from "../../api";
import { OrdersTable } from "../../components/OrdersTable";
import { Spinner } from "../../components/Spinner";
import { OrderDrawer } from "./OrderDrawer";

export function SchoolOrders() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [status, setStatus] = useState<string>("");
  const [q, setQ] = useState("");
  const [focused, setFocused] = useState<Order | null>(null);

  async function load() {
    const data = await api.schoolOrders({ status: status || undefined, q: q || undefined });
    setOrders(data);
  }
  useEffect(() => { load(); }, [status]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-head text-navy">Orders</h1>
        <a href={api.schoolExportUrl} className="btn btn-secondary">Export CSV</a>
      </div>
      <div className="card flex gap-3 items-center">
        <select className="input max-w-xs" value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="pending_payment">Pending payment</option>
          <option value="awaiting_details">Awaiting details</option>
          <option value="generating">Generating</option>
          <option value="generated">Generated</option>
          <option value="failed">Failed</option>
        </select>
        <input className="input max-w-xs" placeholder="Search name, matric, email" value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && load()} />
        <button className="btn btn-primary" onClick={load}>Search</button>
      </div>
      <div className="card p-0 overflow-hidden">
        {!orders ? <Spinner /> : <OrdersTable orders={orders} onRowClick={setFocused} />}
      </div>
      {focused && <OrderDrawer order={focused} onClose={() => setFocused(null)} onChange={load} />}
    </div>
  );
}
