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
  headingLevel?: 1 | 2;
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
          : "flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between",
        "",
        className,
      )}
    />
    <Divider />
  </>
)) as Compound["Header"];
const Divider = (({ className }) => (
  <div className={`border-border mx-6 border-t ${className ?? ""}`} />
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
  headingLevel = 2,
}) => (
  <Card className="gap-0">
    {title || description || actions ? (
      <>
        <Header className={headerClassName}>
          <div className="min-w-0 space-y-1.5">
            {title &&
              (headingLevel === 1 ? (
                <h1 className="text-2xl font-semibold tracking-tight break-words">{title}</h1>
              ) : (
                <h2 className="text-lg font-semibold tracking-tight break-words">{title}</h2>
              ))}
            {description && <Description>{description}</Description>}
          </div>
          {actions && (
            <div className="flex max-w-full flex-wrap items-center gap-2 sm:justify-end">
              {actions}
            </div>
          )}
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
