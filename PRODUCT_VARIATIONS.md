# Product variations

The product editor in Django admin now has a **Product variants** section. Add one row per purchasable combination (for example Small / Black and Large / Black).

- Enter a unique SKU for each combination.
- Fill in Size and/or Color. Use Label for another variation, such as scent, flavor, or material.
- Leave Price CAD blank to inherit the product price, or set the combination's price.
- Set inventory for each combination. Turn off Track inventory for unlimited availability.
- Use Is active to hide a combination from the storefront. Existing bag items with an inactive combination must be removed before checkout.
- Sort order controls the order of the options.

Once a product has variation rows, shoppers must choose a combination on its product page. Variation stock replaces the parent product's stock for these purchases. Products without variation rows continue using their existing price and inventory. If every variation is inactive or out of stock, the product cannot be added to the bag.

The selected variation and SKU are preserved in the bag, checkout quote, PayPal order, customer order detail, and admin order item. Order descriptions remain snapshots even if you later edit variations.

## Deployment

Back up the database and deploy the updated backend and frontend together. Apply the included schema migrations with `python manage.py migrate` before using the updated storefront or admin. These migrations add catalog variations, allow separate cart lines per variation, and add a variation description to order items. They do not create variations for existing products.

No live database migrations or product changes are performed by this source update.
