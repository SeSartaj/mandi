import React from "react";

interface AppTitleProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  others?: React.ReactNode;
}
export default function AppTitle({ title, description, others }: AppTitleProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex min-w-0 flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight break-words">{title}</h1>
        {description && (
          <p className="text-muted-foreground text-sm leading-relaxed">{description}</p>
        )}
      </div>
      {others}
    </div>
  );
}
