import { useEffect, useMemo, useState, type ReactNode } from "react";
import { CloudUpload, FileText, Image as ImageIcon, X } from "lucide-react";
import {
  useWatch,
  type FieldValues,
  type Path,
  type PathValue,
  type RegisterOptions,
  type UseFormReturn,
} from "react-hook-form";
import type { Accept } from "react-dropzone";

import { FileInput, FileUploader, FileUploaderItem } from "@/components/ui/file-upload";
import { useLocale, useTranslations } from "@/i18n/useTranslations";
import { cn } from "@/lib/utils";
import { changeFieldValue, type ClearFieldItem } from "@/utils/form-utils";

import { FormInputLayout } from "./InputLayout";
import { FormField } from "@/components/ui/form";

export type FileType = "pdf" | "image" | "both" | "any";

interface CustomFileInputProps<T extends FieldValues> {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  type?: FileType;
  accept?: Accept;
  maxFiles?: number;
  maxSizeMB?: number;
  clearFieldsOnChange?: ClearFieldItem<T>[];
  description?: ReactNode;
  placeholder?: ReactNode;
  labelClassName?: string;
  containerClassName?: string;
  rules?: RegisterOptions<T, Path<T>>;
  required?: boolean;
  reserveErrorSpace?: boolean;
  disabled?: boolean;
}

function getAccept(type: FileType): Accept | undefined {
  if (type === "pdf") return { "application/pdf": [".pdf"] };
  if (type === "image") {
    return { "image/*": [".jpg", ".jpeg", ".png", ".gif", ".webp"] };
  }
  if (type === "both") {
    return {
      "application/pdf": [".pdf"],
      "image/*": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    };
  }
  return undefined;
}

function getFileIcon(file: File) {
  return file.type.startsWith("image/") ? ImageIcon : FileText;
}

function CustomFileInput<T extends FieldValues>({
  form,
  name,
  label,
  type = "any",
  accept: acceptProp,
  maxFiles = 1,
  maxSizeMB = 4,
  clearFieldsOnChange = [],
  description,
  placeholder,
  labelClassName,
  containerClassName,
  rules,
  required = false,
  reserveErrorSpace = false,
  disabled = false,
}: CustomFileInputProps<T>) {
  const t = useTranslations("Form");
  const locale = useLocale();
  const watchedFile: unknown = useWatch({ control: form.control, name });
  const [files, setFiles] = useState<File[]>([]);

  const direction = locale === "en" ? "ltr" : "rtl";
  const accept = useMemo(() => acceptProp ?? getAccept(type), [acceptProp, type]);
  const maxSize = maxSizeMB * 1024 * 1024;
  const file = files[0] ?? (watchedFile instanceof File ? watchedFile : null);
  const singleFileMode = maxFiles === 1;
  const maxSizeLabel =
    locale === "en" ? "Max size: " + maxSizeMB + " MB" : "لوړه اندازه: " + maxSizeMB + " MB";
  const filePreview = file?.type.startsWith("image/") ? URL.createObjectURL(file) : null;

  useEffect(() => {
    if (watchedFile instanceof File) {
      setFiles((current) => (current[0] === watchedFile ? current : [watchedFile]));
    } else if (Array.isArray(watchedFile)) {
      setFiles(watchedFile.filter((value): value is File => value instanceof File));
    } else if (!watchedFile) {
      setFiles([]);
    }
  }, [watchedFile]);

  useEffect(() => {
    return () => {
      if (filePreview) URL.revokeObjectURL(filePreview);
    };
  }, [filePreview]);

  const handleValueChange = (nextFiles: File[] | null) => {
    const nextFile = nextFiles?.[0] ?? null;
    setFiles(nextFiles ?? []);
    form.setValue(name, (singleFileMode ? nextFile : nextFiles) as PathValue<T, Path<T>>, {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: true,
    });

    if (nextFile && clearFieldsOnChange.length > 0) {
      changeFieldValue(form, clearFieldsOnChange, "", { shouldDirty: true });
    }
  };

  const inputPlaceholder = placeholder ?? (
    <>
      <CloudUpload className="text-muted-foreground mx-auto mb-2 size-8" />
      <span className="text-sm font-medium">
        <span className="text-primary">{t("click_to_upload")}</span> {t("or_drag_drop")}
      </span>
      <span className="text-muted-foreground mt-1 block text-xs">
        {type === "pdf"
          ? t("only_pdf")
          : type === "image"
            ? t("only_images")
            : type === "both"
              ? t("only_pdf_and_images")
              : t("any_file")}
      </span>
    </>
  );

  return (
    <FormField
      control={form.control}
      name={name}
      rules={rules}
      render={() => (
        <FormInputLayout
          label={label}
          required={required}
          labelClassName={labelClassName}
          containerClassName={containerClassName}
          reserveErrorSpace={reserveErrorSpace}
        >
          <div>
            <FileUploader
              value={files}
              onValueChange={handleValueChange}
              reSelect={singleFileMode}
              dir={direction}
              className={cn(disabled && "pointer-events-none opacity-60")}
              dropzoneOptions={{
                accept,
                maxFiles,
                maxSize,
                multiple: maxFiles > 1,
                disabled,
              }}
            >
              <FileInput className="bg-muted/20 hover:bg-muted/40 min-h-28 cursor-pointer border-dashed">
                <div className="flex min-h-28 flex-col items-center justify-center px-4 py-5 text-center">
                  {file && singleFileMode ? (
                    <>
                      {filePreview ? (
                        <img
                          src={filePreview}
                          alt={file.name}
                          className="mb-2 size-8 rounded object-cover"
                        />
                      ) : (
                        (() => {
                          const Icon = getFileIcon(file);
                          return <Icon className="text-muted-foreground mx-auto mb-2 size-8" />;
                        })()
                      )}
                      <span className="text-foreground flex max-w-full items-center gap-2 text-sm font-semibold">
                        <span
                          className="inline-flex max-w-full min-w-0 items-center gap-1"
                          dir={direction}
                        >
                          <span
                            className="min-w-0 truncate whitespace-nowrap"
                            dir="auto"
                            title={file.name}
                          >
                            {file.name}
                          </span>
                          <span className="shrink-0 whitespace-nowrap" dir="ltr">
                            ({(file.size / 1024 / 1024).toFixed(2)} MB)
                          </span>
                        </span>

                        <button
                          type="button"
                          aria-label={locale === "en" ? "Remove file" : "دوتنه لرې کړئ"}
                          className="hover:bg-muted flex shrink-0 items-center justify-center rounded-full p-1"
                          onClick={(event) => {
                            event.stopPropagation();
                            handleValueChange(null);
                          }}
                        >
                          <X className="size-4" />
                        </button>
                      </span>
                    </>
                  ) : (
                    inputPlaceholder
                  )}
                  {!file && (
                    <span className="text-muted-foreground mt-1 block text-xs">{maxSizeLabel}</span>
                  )}
                </div>
              </FileInput>
              {!singleFileMode && files.length > 0 && (
                <div className="w-full px-1">
                  <div className="flex flex-col gap-1">
                    {files.map((selectedFile, index) => {
                      const Icon = getFileIcon(selectedFile);
                      return (
                        <FileUploaderItem
                          key={index}
                          index={index}
                          className="flex h-auto min-h-10 items-center py-2 pe-7"
                        >
                          <Icon className="text-muted-foreground size-5 shrink-0" />
                          <span
                            className="inline-flex min-w-0 flex-1 items-center gap-1 text-xs whitespace-nowrap"
                            dir={direction}
                          >
                            <span className="min-w-0 truncate" dir="auto" title={selectedFile.name}>
                              {selectedFile.name}
                            </span>
                            <span className="shrink-0" dir="ltr">
                              - ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                            </span>
                          </span>
                        </FileUploaderItem>
                      );
                    })}
                  </div>
                </div>
              )}
            </FileUploader>
            {description && <p className="text-muted-foreground mt-1 text-xs">{description}</p>}
          </div>
        </FormInputLayout>
      )}
    />
  );
}

export default CustomFileInput;
