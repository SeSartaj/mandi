"use client";

import { useTranslations } from "@/i18n/useTranslations";
import { AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface AppErrorStateProps {
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function AppErrorState({ message, onRetry, className }: AppErrorStateProps) {
  const tCommon = useTranslations("Common");

  return (
    <Card className={className ?? "border-destructive/30 bg-card shadow-sm"}>
      <CardContent className="flex flex-col items-center justify-center gap-3 p-10 text-center">
        <div className="bg-destructive/10 text-destructive flex size-14 items-center justify-center rounded-full">
          <AlertTriangle className="size-6" />
        </div>
        <span className="text-foreground text-sm font-medium">
          {message ?? tCommon("something_went_wrong")}
        </span>
        {onRetry && (
          <Button variant="outline" onClick={onRetry}>
            {tCommon("retry")}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export default AppErrorState;
