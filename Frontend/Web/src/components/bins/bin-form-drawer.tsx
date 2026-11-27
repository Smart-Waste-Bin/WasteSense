import { useState, type FormEvent, type ReactNode } from "react"
import { toast } from "sonner"
import { createBin, updateBin, type BinRecord } from "@/auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { LocationPicker, type LatLng } from "./location-picker"

const DEFAULT_DUE_THRESHOLD = 70

type FormValues = {
  id: string
  name: string
  sensor_id: string
  depth_cm: string
  volume_l: string
  due_threshold: number
  location: LatLng | null
  is_physical: boolean
  maintenance: boolean
}

type FormErrors = Partial<Record<keyof FormValues, string>>

function formFromBin(bin: BinRecord | null): FormValues {
  if (!bin) {
    return {
      id: "",
      name: "",
      sensor_id: "",
      depth_cm: "",
      volume_l: "",
      due_threshold: DEFAULT_DUE_THRESHOLD,
      location: null,
      is_physical: false,
      maintenance: false,
    }
  }
  return {
    id: bin.id,
    name: bin.name,
    sensor_id: bin.sensor_id ?? "",
    depth_cm: String(bin.depth_cm),
    volume_l: String(bin.volume_l),
    due_threshold: bin.due_threshold ?? DEFAULT_DUE_THRESHOLD,
    location: bin.location,
    is_physical: bin.is_physical,
    maintenance: bin.maintenance,
  }
}

function validateBinForm(form: FormValues, isNew: boolean): FormErrors {
  const errors: FormErrors = {}
  if (isNew && !/^BIN-\d{3,}$/.test(form.id.trim())) {
    errors.id = "Use the format BIN-001."
  }
  if (!form.name.trim()) errors.name = "Enter a name."
  const depth = Number(form.depth_cm)
  if (!form.depth_cm.trim() || !Number.isFinite(depth) || depth < 30 || depth > 200) {
    errors.depth_cm = "Depth must be between 30 and 200 cm."
  }
  const volume = Number(form.volume_l)
  if (!form.volume_l.trim() || !Number.isFinite(volume) || volume <= 0) {
    errors.volume_l = "Enter a volume above 0 litres."
  }
  if (!form.location) errors.location = "Click the map to place the bin."
  return errors
}

function errorForField(message: string): FormErrors {
  if (message.includes("Bin ID")) return { id: message }
  if (message.includes("sensor ID")) return { sensor_id: message }
  return {}
}

type FieldProps = {
  label: string
  error?: string
  children: ReactNode
}

function Field({ label, error, children }: FieldProps) {
  return (
    <label className="block space-y-1.5 text-sm font-medium">
      {label}
      {children}
      {error && <span className="block text-xs font-normal text-red-700">{error}</span>}
    </label>
  )
}

type BinFormProps = {
  bin: BinRecord | null
  onCancel: () => void
  onSaved: (bin: BinRecord) => void
}

function BinForm({ bin, onCancel, onSaved }: BinFormProps) {
  const isNew = bin === null
  const [form, setForm] = useState<FormValues>(() => formFromBin(bin))
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitted, setSubmitted] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const update = <K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    const next = { ...form, [key]: value }
    setForm(next)
    if (submitted) setErrors(validateBinForm(next, isNew))
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitted(true)
    setFormError(null)
    const found = validateBinForm(form, isNew)
    setErrors(found)
    if (Object.keys(found).length > 0 || !form.location) return

    const fields = {
      name: form.name.trim(),
      location: form.location,
      depth_cm: Number(form.depth_cm),
      volume_l: Number(form.volume_l),
      sensor_id: form.sensor_id.trim() || null,
      is_physical: form.is_physical,
    }

    setIsSaving(true)
    try {
      let saved: BinRecord
      if (isNew) {
        saved = await createBin({ ...fields, id: form.id.trim(), due_threshold: form.due_threshold })
        toast.success("Bin added")
      } else {
        const dueChanged = form.due_threshold !== (bin.due_threshold ?? DEFAULT_DUE_THRESHOLD)
        saved = await updateBin(bin.id, {
          ...fields,
          maintenance: form.maintenance,
          ...(dueChanged ? { due_threshold: form.due_threshold } : {}),
        })
        toast.success("Bin updated")
      }
      onSaved(saved)
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "Unable to save this bin."
      const fieldError = errorForField(message)
      if (Object.keys(fieldError).length > 0) {
        setErrors((current) => ({ ...current, ...fieldError }))
      } else {
        setFormError(message)
      }
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <form noValidate onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-4">
        <Field label="Name" error={errors.name}>
          <Input
            value={form.name}
            placeholder="Queens Hall"
            aria-invalid={Boolean(errors.name)}
            onChange={(event) => update("name", event.target.value)}
          />
        </Field>
        <Field label="Bin ID" error={errors.id}>
          <Input
            value={form.id}
            placeholder="BIN-006"
            disabled={!isNew}
            aria-invalid={Boolean(errors.id)}
            onChange={(event) => update("id", event.target.value.toUpperCase())}
          />
        </Field>
        <Field label="Sensor ID (optional)" error={errors.sensor_id}>
          <Input
            value={form.sensor_id}
            aria-invalid={Boolean(errors.sensor_id)}
            onChange={(event) => update("sensor_id", event.target.value)}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Depth (cm)" error={errors.depth_cm}>
            <Input
              type="number"
              min="30"
              max="200"
              value={form.depth_cm}
              aria-invalid={Boolean(errors.depth_cm)}
              onChange={(event) => update("depth_cm", event.target.value)}
            />
          </Field>
          <Field label="Volume (L)" error={errors.volume_l}>
            <Input
              type="number"
              min="1"
              value={form.volume_l}
              aria-invalid={Boolean(errors.volume_l)}
              onChange={(event) => update("volume_l", event.target.value)}
            />
          </Field>
        </div>
        <Field label={`Due threshold: ${form.due_threshold}%`}>
          <input
            type="range"
            min="50"
            max="95"
            step="1"
            className="w-full accent-primary"
            value={form.due_threshold}
            onChange={(event) => update("due_threshold", Number(event.target.value))}
          />
        </Field>
        <div className="space-y-1.5 text-sm font-medium">
          <span>Location</span>
          <LocationPicker value={form.location} onChange={(value) => update("location", value)} />
          {errors.location && (
            <span className="block text-xs font-normal text-red-700">{errors.location}</span>
          )}
        </div>
        <div className="flex flex-wrap gap-5 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.is_physical}
              onChange={(event) => update("is_physical", event.target.checked)}
            />
            Physical bin
          </label>
          {!isNew && (
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.maintenance}
                onChange={(event) => update("maintenance", event.target.checked)}
              />
              Maintenance mode
            </label>
          )}
        </div>
        {formError && (
          <p role="alert" className="text-sm text-red-700">
            {formError}
          </p>
        )}
      </div>
      <SheetFooter className="flex-row justify-end">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isSaving}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSaving}>
          {isSaving ? "Saving..." : isNew ? "Add bin" : "Save changes"}
        </Button>
      </SheetFooter>
    </form>
  )
}

type BinFormDrawerProps = {
  open: boolean
  bin: BinRecord | null
  onClose: () => void
  onSaved: (bin: BinRecord) => void
}

export function BinFormDrawer({ open, bin, onClose, onSaved }: BinFormDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{bin ? `Edit ${bin.id}` : "Add bin"}</SheetTitle>
          <SheetDescription>
            {bin ? "Change the bin's details or move its pin." : "Fill in the details and drop a pin on the map."}
          </SheetDescription>
        </SheetHeader>
        {open && <BinForm bin={bin} onCancel={onClose} onSaved={onSaved} />}
      </SheetContent>
    </Sheet>
  )
}
