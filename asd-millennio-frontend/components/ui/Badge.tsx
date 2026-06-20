import { clsx } from "clsx";

type BadgeVariant = "blue" | "green" | "orange" | "gray" | "red";

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
}

const variants: Record<BadgeVariant, string> = {
  blue: "bg-blue-100 text-blue-800",
  green: "bg-green-100 text-green-800",
  orange: "bg-orange-100 text-orange-800",
  gray: "bg-gray-100 text-gray-600",
  red: "bg-red-100 text-red-800",
};

export function Badge({ variant = "gray", children }: BadgeProps) {
  return (
    <span className={clsx("inline-block rounded-full px-2.5 py-0.5 text-xs font-medium", variants[variant])}>
      {children}
    </span>
  );
}
