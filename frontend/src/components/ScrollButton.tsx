import React from 'react'

export default function ScrollButton({ onClick }: { onClick: () => void }) {
  return (
    <button className="scroll-btn" title="Scroll to bottom" onClick={onClick}>
      ↓
    </button>
  )
}

