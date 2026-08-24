import type { OrderStatus } from "../api";

const styles: Record<OrderStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  pending_payment: "bg-amber-100 text-amber-800",
  awaiting_details: "bg-sky-100 text-sky-800",
  generating: "bg-sky-100 text-sky-800",
  generated: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={"inline-block px-2 py-0.5 rounded-full text-xs font-semibold " + (styles[status] || "bg-gray-100 text-gray-800")}>
      {status.split("_").join(" ")}
    </span>
  );
}
