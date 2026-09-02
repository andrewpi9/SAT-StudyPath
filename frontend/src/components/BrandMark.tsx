export default function BrandMark({ className = 'h-6 w-6' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#4f46e5" />
      <rect x="7" y="17" width="4.5" height="8" rx="1.2" fill="#fff" opacity="0.55" />
      <rect x="13.75" y="12" width="4.5" height="13" rx="1.2" fill="#fff" opacity="0.8" />
      <rect x="20.5" y="7" width="4.5" height="18" rx="1.2" fill="#fff" />
    </svg>
  )
}
