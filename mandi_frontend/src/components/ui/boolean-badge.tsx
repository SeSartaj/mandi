import { cn } from "@/lib/utils";
import { BadgeCheck, BadgeX } from "lucide-react";

function BooleanBadge({ checked }: { checked: boolean }) {
  return (
    <div className="flex items-center justify-center">
      <div
        className={cn(
          "font-xs rounded-full border p-1 shadow-sm backdrop-blur-md transition-all",
          checked
            ? "border-green-400/30 bg-green-500/10 shadow-green-500/10"
            : "border-red-400/30 bg-red-500/10 shadow-red-500/10",
        )}
      >
        {checked ? (
          <BadgeCheck className="text-green-400" size={15} />
        ) : (
          <BadgeX className="text-red-400" size={15} />
        )}
      </div>
    </div>
  );
}

export default BooleanBadge;
