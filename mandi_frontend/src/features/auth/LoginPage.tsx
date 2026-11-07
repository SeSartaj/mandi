import { useMutation } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import LanguageSwitcher from "@/components/translation/LanguageSwitcher";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import CustomForm from "@/components/ui/custom/CustomForm";
import FormInput from "@/components/ui/custom/CustomInput";
import { ThemeToggle } from "@/components/ui/custom/ThemeToggle";
import { api, errorMessage } from "@/lib/api";

export default function LoginPage({ onLogin }: { onLogin: (token: string) => void }) {
  const { t } = useTranslation();
  const form = useForm({ defaultValues: { username: "", password: "" } });
  const mutation = useMutation({
    mutationFn: async (values: { username: string; password: string }) =>
      (await api.post("/auth/login/", values)).data,
    onSuccess: (data) => {
      sessionStorage.setItem("mandi-token", data.token);
      onLogin(data.token);
    },
  });

  return (
    <div className="login-page">
      <div className="login-brand">
        <ShieldCheck size={48} />
        <h1>
          mandi<span>.</span>
        </h1>
        <p>{t("Monitoring & inspection")}</p>
      </div>
      <Card className="login-card">
        <div className="login-controls">
          <ThemeToggle />
          <LanguageSwitcher />
        </div>
        <h2>{t("Sign in")}</h2>
        <p className="muted">{t("Review workspace")}</p>
        <CustomForm
          form={form}
          onSubmit={(values) => mutation.mutate(values)}
          className="space-y-4"
        >
          <FormInput
            form={form}
            name="username"
            label={t("Username")}
            autoComplete="username"
            rules={{ required: t("Required") }}
          />
          <FormInput
            form={form}
            name="password"
            label={t("Password")}
            type="password"
            autoComplete="current-password"
            rules={{ required: t("Required") }}
          />
          {mutation.error ? (
            <div role="alert" className="error-box">
              {errorMessage(mutation.error)}
            </div>
          ) : null}
          <Button className="full" disabled={mutation.isPending}>
            {t("Sign in")}
          </Button>
        </CustomForm>
      </Card>
      <small>{t("Local review build · Live integrations are not connected.")}</small>
    </div>
  );
}
