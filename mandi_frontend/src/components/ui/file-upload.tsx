import {
  createContext,
  forwardRef,
  useCallback,
  useContext,
  useEffect,
  useState,
  type Dispatch,
  type HTMLAttributes,
  type KeyboardEvent,
  type ReactNode,
  type SetStateAction,
} from "react";
import {
  useDropzone,
  type DropzoneOptions,
  type DropzoneState,
  type FileRejection,
} from "react-dropzone";
import { X as RemoveIcon } from "lucide-react";
import { toast } from "sonner";

import { Input } from "@/components/ui/input";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useTranslations } from "@/i18n/useTranslations";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

type Direction = "ltr" | "rtl";
type Orientation = "horizontal" | "vertical";

interface FileUploaderContextValue {
  dropzoneState: DropzoneState;
  isLOF: boolean;
  isFileTooBig: boolean;
  removeFileFromSet: (index: number) => void;
  activeIndex: number;
  setActiveIndex: Dispatch<SetStateAction<number>>;
  orientation: Orientation;
  direction: Direction;
}

interface FileUploaderProps extends HTMLAttributes<HTMLDivElement> {
  value: File[] | null;
  onValueChange: (value: File[] | null) => void;
  dropzoneOptions: DropzoneOptions;
  reSelect?: boolean;
  orientation?: Orientation;
  dir?: Direction;
  children?: ReactNode;
}

const FileUploaderContext = createContext<FileUploaderContextValue | null>(null);

export function useFileUpload() {
  const context = useContext(FileUploaderContext);
  if (!context) {
    throw new Error("useFileUpload must be used within a FileUploader");
  }
  return context;
}

export const FileUploader = forwardRef<HTMLDivElement, FileUploaderProps>(
  (
    {
      className,
      dropzoneOptions,
      value,
      onValueChange,
      reSelect,
      orientation = "vertical",
      children,
      dir,
      ...props
    },
    ref,
  ) => {
    const [isFileTooBig, setIsFileTooBig] = useState(false);
    const [activeIndex, setActiveIndex] = useState(-1);
    const t = useTranslations("Form");
    const {
      accept = { "image/*": [".jpg", ".jpeg", ".png", ".gif"] },
      maxFiles = 1,
      maxSize = 4 * 1024 * 1024,
      multiple = true,
    } = dropzoneOptions;
    const reSelectAll = maxFiles === 1 || reSelect;
    const direction: Direction = dir === "rtl" ? "rtl" : "ltr";

    const removeFileFromSet = useCallback(
      (index: number) => {
        if (!value) return;
        onValueChange(value.filter((_, itemIndex) => itemIndex !== index));
      },
      [onValueChange, value],
    );

    const onDrop = useCallback(
      (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
        if (acceptedFiles.length > 0) {
          const nextFiles = reSelectAll
            ? acceptedFiles.slice(0, maxFiles)
            : [
                ...(value ?? []),
                ...acceptedFiles.slice(0, Math.max(0, maxFiles - (value?.length ?? 0))),
              ];
          onValueChange(nextFiles);
        }

        if (rejectedFiles.length > 0) {
          const rejection = rejectedFiles[0];
          if (rejection.errors[0]?.code === "file-too-large") {
            toast.error(t("file_too_large", { maxSizeMB: maxSize / 1024 / 1024 }));
          } else if (rejection.errors[0]?.message) {
            toast.error(rejection.errors[0].message);
          } else {
            toast.error(t("file_error"));
          }
        }
      },
      [maxFiles, maxSize, onValueChange, reSelectAll, t, value],
    );

    const dropzoneState = useDropzone({
      ...dropzoneOptions,
      accept,
      maxFiles,
      maxSize,
      multiple,
      onDrop,
      onDropRejected: () => setIsFileTooBig(true),
      onDropAccepted: () => setIsFileTooBig(false),
    });
    const isLOF = Boolean(value && value.length >= maxFiles && !reSelectAll);

    useEffect(() => {
      if (!value || activeIndex < value.length) return;
      setActiveIndex(value.length - 1);
    }, [activeIndex, value]);

    const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
      if (!value?.length) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          dropzoneState.open();
        }
        return;
      }

      const previousKey =
        orientation === "horizontal"
          ? direction === "ltr"
            ? "ArrowLeft"
            : "ArrowRight"
          : "ArrowUp";
      const nextKey =
        orientation === "horizontal"
          ? direction === "ltr"
            ? "ArrowRight"
            : "ArrowLeft"
          : "ArrowDown";

      if (event.key === nextKey) {
        event.preventDefault();
        setActiveIndex((index) => (index + 1) % value.length);
      } else if (event.key === previousKey) {
        event.preventDefault();
        setActiveIndex((index) => (index <= 0 ? value.length - 1 : index - 1));
      } else if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (activeIndex === -1 && !isLOF) dropzoneState.open();
      } else if (event.key === "Delete" || event.key === "Backspace") {
        event.preventDefault();
        if (activeIndex !== -1) {
          removeFileFromSet(activeIndex);
          setActiveIndex((index) => (value.length <= 1 ? -1 : Math.max(0, index - 1)));
        }
      } else if (event.key === "Escape") {
        setActiveIndex(-1);
      }
    };

    return (
      <FileUploaderContext.Provider
        value={{
          dropzoneState,
          isLOF,
          isFileTooBig,
          removeFileFromSet,
          activeIndex,
          setActiveIndex,
          orientation,
          direction,
        }}
      >
        <div
          ref={ref}
          tabIndex={0}
          onKeyDown={handleKeyDown}
          className={cn("grid w-full overflow-hidden focus:outline-none", className, {
            "gap-2": Boolean(value?.length),
          })}
          dir={dir}
          {...props}
        >
          {children}
        </div>
      </FileUploaderContext.Provider>
    );
  },
);

FileUploader.displayName = "FileUploader";

export const FileUploaderContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ children, className, ...props }, ref) => {
    const { orientation } = useFileUpload();
    return (
      <div className="w-full px-1">
        <div
          {...props}
          ref={ref}
          className={cn(
            "flex gap-1 rounded-xl",
            orientation === "horizontal" ? "flex-row flex-wrap" : "flex-col",
            className,
          )}
        >
          {children}
        </div>
      </div>
    );
  },
);

FileUploaderContent.displayName = "FileUploaderContent";

interface FileUploaderItemProps extends HTMLAttributes<HTMLDivElement> {
  index: number;
}

export const FileUploaderItem = forwardRef<HTMLDivElement, FileUploaderItemProps>(
  ({ className, index, children, ...props }, ref) => {
    const { removeFileFromSet, activeIndex, direction } = useFileUpload();
    const isSelected = index === activeIndex;
    return (
      <div
        ref={ref}
        className={cn(
          buttonVariants({ variant: "ghost" }),
          "relative h-6 cursor-pointer justify-between p-1",
          isSelected && "bg-muted",
          className,
        )}
        {...props}
      >
        <div className="flex h-full w-full items-center gap-1.5 leading-none font-medium tracking-tight">
          {children}
        </div>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              tabIndex={-1}
              aria-label={
                direction === "rtl" ? "دا فایل له فورم څخه لرې کړئ" : "Remove file from the form"
              }
              className={cn(
                "absolute top-1/2 -translate-y-1/2 rounded p-1",
                direction === "rtl" ? "left-1" : "right-1",
              )}
              onClick={(event) => {
                event.stopPropagation();
                removeFileFromSet(index);
              }}
            >
              <RemoveIcon className="hover:stroke-destructive size-4" />
            </button>
          </TooltipTrigger>
          <TooltipContent>
            {direction === "rtl" ? "دا فایل له فورم څخه لرې کړئ" : "Remove file from the form"}
          </TooltipContent>
        </Tooltip>
      </div>
    );
  },
);

FileUploaderItem.displayName = "FileUploaderItem";

export const FileInput = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    const { dropzoneState, isFileTooBig, isLOF } = useFileUpload();
    const rootProps = isLOF ? {} : dropzoneState.getRootProps();
    const inputProps = dropzoneState.getInputProps();

    return (
      <div ref={ref} {...props} className="relative w-full">
        <div
          className={cn(
            "w-full rounded-lg border border-gray-300 transition-colors duration-300",
            isLOF && "cursor-not-allowed opacity-50",
            dropzoneState.isDragAccept && "border-green-500",
            (dropzoneState.isDragReject || isFileTooBig) && "border-red-500",
            className,
          )}
          {...rootProps}
        >
          {children}
        </div>
        <Input disabled={isLOF} {...inputProps} className={cn(inputProps.className, "sr-only")} />
      </div>
    );
  },
);

FileInput.displayName = "FileInput";
