"use client"

import { useState } from "react"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { useAutoResizeTextarea } from "@/components/hooks/use-auto-resize-textarea"

interface AIInputProps {
  id?: string
  placeholder?: string
  minHeight?: number
  maxHeight?: number
  onSubmit?: (value: string) => void | Promise<void>
  className?: string
}

export function AIInput({
  id = "ai-input",
  placeholder = "Ask me anything!",
  minHeight = 56,
  maxHeight = 200,
  onSubmit,
  className,
}: AIInputProps) {
  const [inputValue, setInputValue] = useState("")

  const { textareaRef, adjustHeight } = useAutoResizeTextarea({
    minHeight,
    maxHeight,
  })

  const handleSubmit = async () => {
    if (!inputValue.trim()) return
    await onSubmit?.(inputValue)
    setInputValue("")
    adjustHeight(true)
  }

  return (
    <div className={cn("w-full py-4", className)}>
      <div className="relative max-w-xl w-full mx-auto">
        <Textarea
          id={id}
          placeholder={placeholder}
          className={cn(
            "max-w-xl bg-background/80 backdrop-blur-sm w-full rounded-md pl-6 pr-10 py-4",
            "placeholder:text-black/70 dark:placeholder:text-white/70",
            "text-black dark:text-white resize-none text-wrap leading-[1.2]",
            "text-xl",
            "border border-input",
            "overflow-hidden",
            `min-h-[${minHeight}px]`,
          )}
          ref={textareaRef}
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value)
            adjustHeight()
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              handleSubmit()
            }
          }}
        />
        {/* <button
          onClick={handleSubmit}
          className="absolute right-3 top-1/2 -translate-y-1/2 rounded-xl py-1 px-1 bg-black/5 dark:bg-white/5"
          type="button"
        >
          <CornerRightUp
            className={cn("w-5 h-5 transition-opacity dark:text-white", inputValue ? "opacity-100" : "opacity-30")}
          />
        </button> */}
      </div>
    </div>
  )
}

