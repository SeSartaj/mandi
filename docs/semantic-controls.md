# Semantic actions and stable field messages

Use the shared components from `mandi_frontend/src/components/public/ActionButton.tsx` for create, edit, save, cancel, delete, and discard actions. Existing business actions and file removal controls use these wrappers; navigation, filtering, synchronization, and connection actions keep their own meanings.

```tsx
<CreateButton label={t("Add establishment")} onClick={openForm} />
<EditButton variant="secondary" onClick={openEditor} />
<SaveButton loading={saving} />
<CancelButton onClick={cancel} />
<DeleteButton iconOnly variant="secondary" label={t("Remove file")} onClick={removeFile} />
```

All actions support `variant="primary" | "secondary"`, `iconOnly`, a translated `label`, `loading`, `loadingLabel`, and `size="xs" | "sm" | "default" | "lg"`. Labels are translated automatically when omitted. Icon-only actions receive an accessible name and native tooltip. Use a specific label when multiple record actions appear together.

Meaning and emphasis are separate: delete and discard remain destructive in either emphasis. Discard uses an undo icon rather than claiming that an unsaved draft is a deleted record. Loading replaces the action icon with a spinner and disables the button. The default HTML type is `submit` for Save and `button` for other actions. Override `type` explicitly when needed. Native button props, event handlers, and refs pass through, including through Radix `DialogClose asChild`.

Email and password values use semantic inputs. Prefer the `EmailInput` and `PasswordInput` wrappers in `mandi_frontend/src/components/ui/custom/CustomInput.tsx`; plain `Input type="email"` and `Input type="password"` get the same treatment from the shared input layer. These fields always render `dir="ltr"`, disable autocapitalise/autocorrect/spellcheck, and use the matching keyboard hints (`inputMode="email"`, `"tel"`, `"url"`), even when the interface language is Pashto or Dari.

The shared `FieldSupport` reserves a fixed 32px/two-line slot under each control. It is present when empty, contains help when available, and replaces help with an error during validation. Longer text wraps and scrolls within the slot, so its height never pushes later controls. Populated messages are keyboard-focusable for scrolling; empty slots are hidden from assistive technology. Errors use `role="alert"`.

React Hook Form `FormMessage`, the custom field layouts, and the standalone `FormField` all use this slot. Text inputs, selects, textareas, and file inputs accept `description` for help text. Historical `reserveErrorSpace` props remain compatible, but spacing is always reserved even if a caller passes `false`. Form-level request feedback and XLSForm metadata status also reserve message space so centered dialogs keep their position.

Verification includes button semantics/emphasis/loading/localization tests, message priority/ARIA tests, and a browser measurement confirming identical control coordinates before and after required-field validation in English and Pashto. At 390px, all message slots remain 32px high and relative control positions stay unchanged. The production build, formatting checks, and 14 regression tests pass; the inherited lint warnings remain.
