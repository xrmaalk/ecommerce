import type { Product } from "./catalog"

export interface ServerCartItem {
  product: Product
  quantity: number
  unit_price_cad: string
  line_total_cad: string
}

export interface ServerCart {
  id: string
  currency: "CAD"
  items: ServerCartItem[]
  item_count: number
  subtotal_cad: string
  updated_at: string
}

export interface ShippingRate {
  country_code: "CA" | "US"
  country: string
  name: string
  amount_cad: string
  estimated_days_min: number
  estimated_days_max: number
}

export interface ShippingAddress {
  first_name: string
  last_name: string
  address_line_1: string
  address_line_2: string
  city: string
  region: string
  postal_code: string
  country_code: "CA" | "US"
  phone: string
}

export interface CheckoutLineItem {
  product_id: number
  sku: string
  name: string
  quantity: number
  unit_price_cad: string
  line_total_cad: string
}

export interface CheckoutSession {
  id: string
  status: string
  currency: "CAD"
  shipping_address: ShippingAddress
  line_items: CheckoutLineItem[]
  subtotal_cad: string
  shipping_cad: string
  tax_cad: string
  total_cad: string
  tax_provider: string
  paypal_order_id: string | null
  created_at: string
}

export interface CheckoutConfig {
  paypal_client_id: string
  paypal_mode: "sandbox" | "live"
  currency: "CAD"
  paypal_enabled: boolean
}

export interface OrderItem {
  sku: string
  name: string
  quantity: number
  unit_price_cad: string
  line_total_cad: string
}

export interface Order {
  id: string
  number: string
  status: string
  currency: "CAD"
  customer_email: string
  shipping_address: ShippingAddress
  subtotal_cad: string
  shipping_cad: string
  tax_cad: string
  total_cad: string
  items: OrderItem[]
  paid_at: string
  created_at: string
}

