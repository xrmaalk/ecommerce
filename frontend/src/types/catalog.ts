export interface Category { id:number; name:string; slug:string; description:string }
export interface ProductImage { id:number; image:string; alt_text:string; sort_order:number }
export interface Product { id:number; name:string; slug:string; sku:string; category:Category; short_description:string; description:string; price_cad:string; compare_at_price_cad:string|null; inventory_quantity:number; in_stock:boolean; is_featured:boolean; images:ProductImage[] }
export interface PaginatedProducts { count:number; next:string|null; previous:string|null; results:Product[] }
