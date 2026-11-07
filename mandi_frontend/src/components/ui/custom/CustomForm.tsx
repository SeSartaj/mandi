import { FieldValues, SubmitHandler, UseFormReturn } from "react-hook-form";
import { FormHTMLAttributes, ReactNode } from "react";
import { Form } from "../form";

interface CustomFormProps<TFormValues extends FieldValues> extends Omit<
  FormHTMLAttributes<HTMLFormElement>,
  "onSubmit"
> {
  form: UseFormReturn<TFormValues>;
  onSubmit: SubmitHandler<TFormValues>;
  children: ReactNode;
}

function CustomForm<TFormValues extends FieldValues = FieldValues>({
  form,
  onSubmit,
  children,
  ...props
}: CustomFormProps<TFormValues>) {
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} {...props}>
        {children}
      </form>
    </Form>
  );
}

export default CustomForm;
