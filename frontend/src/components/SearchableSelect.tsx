import { useState, useRef, useEffect } from 'react'

interface SearchableSelectProps {
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  multiple?: boolean
  className?: string
}

export default function SearchableSelect({
  options,
  selected,
  onChange,
  placeholder = 'Search and select...',
  multiple = false,
  className = '',
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filteredOptions = options.filter(option =>
    option.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleSelect = (option: string) => {
    if (multiple) {
      if (selected.includes(option)) {
        onChange(selected.filter(item => item !== option))
      } else {
        onChange([...selected, option])
      }
    } else {
      onChange([option])
      setIsOpen(false)
      setSearchTerm('')
    }
  }

  const removeSelected = (option: string) => {
    onChange(selected.filter(item => item !== option))
  }

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <div
        className="min-h-[38px] w-full px-3 py-2 border border-gray-300 rounded-md bg-white cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        onClick={() => setIsOpen(!isOpen)}
      >
        {selected.length === 0 ? (
          <span className="text-gray-500">{placeholder}</span>
        ) : (
          <div className="flex flex-wrap gap-1">
            {selected.map((item) => (
              <span
                key={item}
                className="inline-flex items-center px-2 py-1 rounded-md bg-indigo-100 text-indigo-800 text-sm"
              >
                {item}
                {multiple && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      removeSelected(item)
                    }}
                    className="ml-1 text-indigo-600 hover:text-indigo-800"
                  >
                    ×
                  </button>
                )}
              </span>
            ))}
          </div>
        )}
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
          <div className="sticky top-0 bg-white p-2 border-b">
            <input
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Type to search..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              autoFocus
            />
          </div>
          <div className="py-1">
            {filteredOptions.length === 0 ? (
              <div className="px-4 py-2 text-sm text-gray-500">No options found</div>
            ) : (
              filteredOptions.map((option) => (
                <div
                  key={option}
                  className={`px-4 py-2 cursor-pointer hover:bg-indigo-50 ${
                    selected.includes(option) ? 'bg-indigo-100' : ''
                  }`}
                  onClick={() => handleSelect(option)}
                >
                  <div className="flex items-center">
                    {multiple && (
                      <input
                        type="checkbox"
                        checked={selected.includes(option)}
                        onChange={() => {}}
                        className="mr-2"
                      />
                    )}
                    <span className="text-sm text-gray-900">{option}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

