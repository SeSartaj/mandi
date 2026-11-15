import { FieldValues, SubmitHandler, UseFormReturn } from "react-hook-form";
import { useContext, useEffect, type FormHTMLAttributes, type ReactNode } from "react";
import { DialogFormState } from "@/components/public/dialog-form-state";
import { Form } from "../form";

interface CustomFormProps<TFormValues extends FieldValues> extends Omit<
  FormHTMLAttributes<HTMLFormElement>,
  "onSubmit"
> {
  form: UseFormReturn<TFormValues>;
  onSubmit: SubmitHandler<TFormValues>;
  children: ReactNode;
  busy?: boolean;
}

function CustomForm<TFormValues extends FieldValues = FieldValues>({
  form,
  onSubmit,
  children,
  busy = false,
  ...props
}: CustomFormProps<TFormValues>) {
  const setDialogState = useContext(DialogFormState);
  const dirty = form.formState.isDirty;
  useEffect(() => {
    setDialogState?.({ dirty, busy });
    return () => setDialogState?.({ dirty: false, busy: false });
  }, [setDialogState, dirty, busy]);

  useEffect(() => {
    if (!setDialogState || !dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [setDialogState, dirty]);

  return (
    <Form {...form}>
      <form
        aria-busy={busy}
        onSubmit={form.handleSubmit((values, event) => {
          if (!busy) return onSubmit(values, event);
        })}
        {...props}
      >
        <fieldset disabled={busy} className="contents">
          {children}
        </fieldset>
      </form>
    </Form>
  );
}

export default CustomForm;
