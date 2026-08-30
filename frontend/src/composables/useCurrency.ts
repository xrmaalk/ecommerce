const cadFormatter = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" })

export function formatCad(value: number): string {
  return cadFormatter.format(Number.isFinite(value) ? value : 0)
}
