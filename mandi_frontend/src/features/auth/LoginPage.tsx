import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import LanguageSwitcher from "@/components/translation/LanguageSwitcher";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import CustomForm from "@/components/ui/custom/CustomForm";
import { EmailInput, PasswordInput } from "@/components/ui/custom/CustomInput";
import { ThemeToggle } from "@/components/ui/custom/ThemeToggle";
import { isRTL } from "@/config/languages";
import { useLocale } from "@/i18n/useTranslations";
import { api, errorMessage } from "@/lib/api";
import { notify } from "@/lib/notify";

export default function LoginPage({
  onLogin,
  sessionExpired = false,
}: {
  onLogin: (token: string) => void;
  sessionExpired?: boolean;
}) {
  const { t } = useTranslation();
  const rtl = isRTL(useLocale());
  const form = useForm({ defaultValues: { email: "", password: "" } });
  const mutation = useMutation({
    mutationFn: async (values: { email: string; password: string }) =>
      (await api.post("/auth/login/", values)).data,
    onSuccess: (data) => {
      sessionStorage.setItem("mandi-token", data.token);
      onLogin(data.token);
    },
    onError: (error) =>
      notify.error(t("Sign-in failed."), {
        description: errorMessage(error),
      }),
  });

  return (
    <main
      dir={rtl ? "rtl" : "ltr"}
      className="bg-muted/30 relative flex min-h-screen items-center justify-center p-6"
    >
      <div className="absolute end-4 top-4 z-10 flex items-center gap-2">
        <ThemeToggle />
        <LanguageSwitcher />
      </div>

      <Card className="w-full max-w-3xl overflow-hidden py-0 shadow-xl">
        <CardContent className="grid p-0 md:grid-cols-2">
          <div className="bg-primary text-primary-foreground relative hidden min-h-[500px] flex-col items-center justify-start gap-2 px-10 pt-16 md:flex">
            <img
              src="/afda_logo.png"
              alt="AFDA"
              className="size-[48px] object-contain brightness-0 invert"
            />
            <h2 className="mt-2 max-w-[15rem] text-center text-xs text-balance">
              {t("Afghanistan Food and Drug Authority")}
            </h2>
            <h1 className="mt-8 text-center text-xl font-semibold">
              {t("Monitoring & inspection")}
            </h1>
            <p className="text-sm opacity-80">{t("Monitoring & inspection")}</p>

            <div className="border-primary-foreground/30 mt-8 w-full max-w-xs border-t pt-5 text-center">
              <p className="text-sm leading-6 font-semibold">
                {t("Digital inspection workspace")}
              </p>
              <p className="mt-1 text-xs leading-5 opacity-80">
                {t("Establishments, checklists and inspection results in one place.")}
              </p>
            </div>

            <div className="mx-10 mt-auto mb-10 w-full px-10">
              <div className="border-primary-foreground/70 relative flex items-center justify-center border">
                <div className="bg-primary absolute z-10 flex w-16 items-center justify-center gap-1 p-3">
                  <span className="size-1.5 rounded-full bg-current" />
                  <span className="size-1.5 rounded-full bg-current" />
                  <span className="size-1.5 rounded-full bg-current" />
                </div>
              </div>
            </div>
          </div>

          <CustomForm
            busy={mutation.isPending}
            form={form}
            onSubmit={(values) => mutation.mutate(values)}
            className="my-6 flex flex-col gap-6 p-6 md:p-8"
          >
            <div className="flex flex-col items-center text-center">
              <img src="/afda_logo.png" alt="AFDA" className="h-20 w-20 object-contain" />
              <h2 className="mt-4 text-2xl font-semibold">{t("Sign in")}</h2>
              <p className="text-muted-foreground mt-1 text-sm text-balance">
                {t("Sign in to your monitoring and inspection workspace.")}
              </p>
              {sessionExpired && (
                <p role="status" className="text-muted-foreground mt-1 text-sm">
                  {t("Your session expired. Please sign in again.")}
                </p>
              )}
            </div>

            <div className="grid gap-4">
              <EmailInput
                form={form}
                name="email"
                label={t("Email")}
                autoFocus
                reserveErrorSpace={false}
                rules={{ required: t("Required") }}
              />
              <PasswordInput
                form={form}
                name="password"
                label={t("Password")}
                reserveErrorSpace={false}
                rules={{ required: t("Required") }}
              />
              {mutation.error && (
                <p role="alert" className="text-destructive text-sm">
                  {errorMessage(mutation.error)}
                </p>
              )}
            </div>

            <Button type="submit" className="w-full" disabled={mutation.isPending}>
              {mutation.isPending ? t("Signing in…") : t("Sign in")}
            </Button>

            <div className="text-muted-foreground after:border-border relative text-center text-xs select-none after:absolute after:inset-x-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t">
              <span className="bg-card text-muted-foreground relative z-10 rounded-xs px-1 py-0.5">
                {t("Afghanistan Food and Drug Authority")}
              </span>
            </div>
          </CustomForm>
        </CardContent>
      </Card>
    </main>
  );
}
