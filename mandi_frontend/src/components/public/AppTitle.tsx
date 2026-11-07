import React from "react";

interface AppTitleProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  others?: React.ReactNode;
}
export default function AppTitle({ title, description, others }: AppTitleProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold">{title}</h1>
        {description && <p className="text-sm">{description}</p>}
      </div>
      {others}
    </div>
  );
}
