import { resolveMediaUrl } from "@/lib/api";

const SIZES = {
  sm: "w-9 h-9 text-xs",
  md: "w-12 h-12 text-base",
  lg: "w-24 h-24 text-3xl",
} as const;

interface AvatarProps {
  name: string;
  avatarUrl?: string | null;
  size?: keyof typeof SIZES;
  className?: string;
}

const Avatar = ({ name, avatarUrl, size = "md", className = "" }: AvatarProps) => {
  const src = resolveMediaUrl(avatarUrl);
  const initial = (name || "?").trim().charAt(0).toUpperCase() || "?";

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        className={`${SIZES[size]} rounded-xl object-cover shrink-0 ${className}`}
      />
    );
  }

  return (
    <div
      className={`${SIZES[size]} rounded-xl gradient-primary flex items-center justify-center text-primary-foreground font-bold shrink-0 ${className}`}
    >
      {initial}
    </div>
  );
};

export default Avatar;
