import type { FC, ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Props = {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  contentClassName?: string;
  headerClassName?: string;
  compound?: boolean;
};
type HeaderProps = React.ComponentProps<typeof CardHeader> & {
  positionMode?: "default" | "centered";
};
type Compound = FC<Props> & {
  Header: FC<HeaderProps>;
  Title: FC<React.ComponentProps<typeof CardTitle>>;
  Description: FC<React.ComponentProps<typeof CardDescription>>;
  Actions: FC<{ children: ReactNode; className?: string }>;
  Content: FC<React.ComponentProps<typeof CardContent>>;
  Divider: FC<{ className?: string }>;
};

const Header = (({ className, positionMode = "default", ...props }) => (
  <>
    <CardHeader
      {...props}
      className={cn(
        positionMode === "centered"
          ? "relative flex flex-col items-center gap-1.5 text-center [&>[data-page-section-actions]]:absolute [&>[data-page-section-actions]]:end-6 [&>[data-page-section-actions]]:top-6"
          : "grid grid-cols-[1fr_auto] items-start gap-x-4 gap-y-1.5 [&>[data-page-section-actions]]:col-start-2 [&>[data-page-section-actions]]:row-span-2 [&>[data-slot=card-description]]:col-start-1 [&>[data-slot=card-title]]:col-start-1",
        "",
        className,
      )}
    />
    <Divider />
  </>
)) as Compound["Header"];
const Divider = (({ className }) => (
  <div className={`border-border mx-6 border-t-2 ${className ?? ""}`} />
)) as Compound["Divider"];
const Title: Compound["Title"] = ({ className, ...props }) => (
  <CardTitle {...props} className={cn("text-2xl tracking-tight", className)} />
);
const Description: Compound["Description"] = ({ className, ...props }) => (
  <CardDescription {...props} className={cn("text-muted-foreground", className)} />
);

const PageSectionBase: FC<Props> = ({
  title,
  description,
  actions,
  children,
  contentClassName,
  headerClassName,
  compound = false,
}) => (
  <Card className="gap-0">
    {title || description || actions ? (
      <>
        <Header className={`flex-row items-start justify-between gap-4 ${headerClassName ?? ""}`}>
          <div className="space-y-1.5">
            {title && <Title>{title}</Title>}
            {description && <Description>{description}</Description>}
          </div>
          {actions}
        </Header>
        <CardContent className={contentClassName ?? "pt-6"}>{children}</CardContent>
      </>
    ) : compound ? (
      children
    ) : (
      <CardContent className={cn("py-0", contentClassName)}>{children}</CardContent>
    )}
  </Card>
);

const PageSection = Object.assign(PageSectionBase, {
  Header,
  Title,
  Description,
  Actions: (({ children, className }) => (
    <div
      data-page-section-actions
      className={cn("flex flex-wrap items-center justify-end gap-2", className)}
    >
      {children}
    </div>
  )) as Compound["Actions"],
  Content: CardContent,
  Divider,
}) as Compound;

export { PageSection };
