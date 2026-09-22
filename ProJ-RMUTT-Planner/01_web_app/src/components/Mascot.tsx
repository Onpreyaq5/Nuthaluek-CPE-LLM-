import { cn } from "@/lib/utils";

export function Mascot({
  avatar = false,
  className = "",
}: {
  avatar?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(avatar ? "mascot-avatar" : "mascot-full", className)}
      aria-hidden="true"
    >
      <img src="/mascot.png" alt="" draggable={false} />
    </span>
  );
}
