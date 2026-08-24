import type { Order } from "../api";
import { fmtDate, fmtNaira } from "../api";
import { StatusBadge } from "./StatusBadge";

export function OrdersTable({ orders, onRowClick }: { orders: Order[]; onRowClick?: (o: Order) => void }) {
  if (orders.length === 0) return <div className="text-gray-500 text-sm py-6 text-center">No orders.</div>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
          <tr>
            <th className="text-left p-3">ID</th>
            <th className="text-left p-3">Student</th>
            <th className="text-left p-3">Matric</th>
            <th className="text-left p-3">Package</th>
            <th className="text-right p-3">Amount</th>
            <th className="text-left p-3">Status</th>
            <th className="text-left p-3">Created</th>
          </tr>
        </thead>
        <tbody>
          {orders.map(o => (
            <tr
              key={o.id}
              className={"border-t border-gray-100 hover:bg-gray-50 " + (onRowClick ? "cursor-pointer" : "")}
              onClick={() => onRowClick?.(o)}
            >
              <td className="p-3 font-mono text-xs">{o.id}{o.express ? " ⚡" : ""}{o.test_mode ? " 🧪" : ""}</td>
              <td className="p-3">{o.student_name}</td>
              <td className="p-3 font-mono text-xs">{o.matric_no}</td>
              <td className="p-3">{o.package}</td>
              <td className="p-3 text-right">{fmtNaira(o.amount)}</td>
              <td className="p-3"><StatusBadge status={o.status} /></td>
              <td className="p-3 text-gray-500">{fmtDate(o.created_at, true)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
