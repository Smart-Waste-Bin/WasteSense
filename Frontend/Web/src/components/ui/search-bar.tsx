import * as React from "react";
import { Search, X } from "lucide-react";
import { cn } from "cn";

import { Input } from "./input";

type SearchSuggestion = {
  id: string;
  label: string;
  description?: string;
};

type SearchBarProps = {
  value?: string;
  defaultValue?: string;
  placeholder?: string;
  ariaLabel?: string;
  suggestions?: SearchSuggestion[];
  className?: string;
  onChange?: (value: string) => void;
  onSearch?: (value: string) => void;
  onSelect?: (suggestion: SearchSuggestion) => void;
};

function SearchBar({
  value,
  defaultValue = "",
  placeholder = "Search...",
  ariaLabel = "Search",
  suggestions = [],
  className,
  onChange,
  onSearch,
  onSelect,
}: SearchBarProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue);
  const [isFocused, setIsFocused] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(-1);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const query = value ?? internalValue;

  const matches = React.useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return [];

    return suggestions
      .filter((suggestion) =>
        `${suggestion.label} ${suggestion.description ?? ""}`
          .toLowerCase()
          .includes(normalizedQuery),
      )
      .slice(0, 6);
  }, [query, suggestions]);

  React.useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  const updateValue = (nextValue: string) => {
    if (value === undefined) setInternalValue(nextValue);
    setActiveIndex(-1);
    onChange?.(nextValue);
  };

  const clearSearch = () => {
    updateValue("");
    setActiveIndex(-1);
    inputRef.current?.focus();
  };

  const selectSuggestion = (suggestion: SearchSuggestion) => {
    updateValue(suggestion.label);
    setIsFocused(false);
    setActiveIndex(-1);
    onSelect?.(suggestion);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (activeIndex >= 0 && matches[activeIndex]) {
      selectSuggestion(matches[activeIndex]);
      return;
    }

    onSearch?.(query.trim());
  };

  const showSuggestions = isFocused && matches.length > 0;

  return (
    <form
      role="search"
      className={cn("relative w-full", className)}
      onSubmit={handleSubmit}
    >
      <Search
        size={18}
        className="pointer-events-none absolute left-3 top-1/2 z-10 -translate-y-1/2 text-slate-400"
      />
      <Input
        ref={inputRef}
        type="search"
        value={query}
        placeholder={placeholder}
        aria-label={ariaLabel}
        aria-expanded={showSuggestions}
        aria-controls="search-suggestions"
        aria-activedescendant={
          activeIndex >= 0 ? `search-suggestion-${activeIndex}` : undefined
        }
        className="h-9 w-full rounded-xl pl-10 pr-10"
        onChange={(event) => updateValue(event.target.value)}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" && matches.length > 0) {
            event.preventDefault();
            setActiveIndex((index) => (index + 1) % matches.length);
          } else if (event.key === "ArrowUp" && matches.length > 0) {
            event.preventDefault();
            setActiveIndex((index) =>
              index <= 0 ? matches.length - 1 : index - 1,
            );
          } else if (event.key === "Escape") {
            setIsFocused(false);
          }
        }}
      />
      {query && (
        <button
          type="button"
          aria-label="Clear search"
          className="absolute right-2 top-1/2 flex size-6 -translate-y-1/2 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          onMouseDown={(event) => event.preventDefault()}
          onClick={clearSearch}
        >
          <X size={14} />
        </button>
      )}
      {showSuggestions && (
        <div
          id="search-suggestions"
          role="listbox"
          className="absolute left-0 top-[calc(100%+0.5rem)] z-50 w-full overflow-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-lg"
        >
          {matches.map((suggestion, index) => (
            <button
              id={`search-suggestion-${index}`}
              key={suggestion.id}
              type="button"
              role="option"
              aria-selected={activeIndex === index}
              className={cn(
                "flex w-full items-center justify-between rounded-lg px-3 py-2 text-left",
                activeIndex === index
                  ? "bg-emerald-50"
                  : "hover:bg-slate-50",
              )}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => selectSuggestion(suggestion)}
            >
              <span className="text-sm font-semibold text-slate-900">
                {suggestion.label}
              </span>
              {suggestion.description && (
                <span className="ml-3 text-xs text-slate-400">
                  {suggestion.description}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </form>
  );
}

export { SearchBar };
export type { SearchBarProps, SearchSuggestion };
