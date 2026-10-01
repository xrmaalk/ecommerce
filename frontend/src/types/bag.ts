export interface BagItem {
  id: number
  key: string
  variantId: number | null
  variation: string
  trackInventory: boolean
  name: string
  slug: string
  price: number
  image: string
  imageAlt: string
  quantity: number
  inventoryQuantity: number
}
