import { onMounted } from "vue";
import { useCatalogStore } from "./stores/catalog";
const store = useCatalogStore();
onMounted(async () => {
    await Promise.all([store.loadCategories(), store.loadProducts()]);
});
let debounce;
function search() {
    window.clearTimeout(debounce);
    debounce = window.setTimeout(store.loadProducts, 300);
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_elements;
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__fallback']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__fallback']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__fallback']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__content']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__content']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__footer']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__footer']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__footer']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__footer']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__footer']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__footer']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__footer']} */ ;
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__footer']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "announcement" },
});
__VLS_asFunctionalElement(__VLS_elements.a, __VLS_elements.a)({
    href: "https://organicarchives.organicemperor.com",
});
__VLS_asFunctionalElement(__VLS_elements.header, __VLS_elements.header)({});
__VLS_asFunctionalElement(__VLS_elements.a, __VLS_elements.a)({
    ...{ class: "brand" },
    href: "/",
});
__VLS_asFunctionalElement(__VLS_elements.i, __VLS_elements.i)({});
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
__VLS_asFunctionalElement(__VLS_elements.small, __VLS_elements.small)({});
__VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
__VLS_asFunctionalElement(__VLS_elements.form, __VLS_elements.form)({
    ...{ onSubmit: (__VLS_ctx.store.loadProducts) },
});
// @ts-ignore
[store,];
__VLS_asFunctionalElement(__VLS_elements.input)({
    ...{ onInput: (__VLS_ctx.search) },
    placeholder: "Search body care, shave care, teas…",
});
(__VLS_ctx.store.query);
// @ts-ignore
[store, search,];
__VLS_asFunctionalElement(__VLS_elements.button, __VLS_elements.button)({});
__VLS_asFunctionalElement(__VLS_elements.nav, __VLS_elements.nav)({});
__VLS_asFunctionalElement(__VLS_elements.a, __VLS_elements.a)({
    href: "#catalog",
});
__VLS_asFunctionalElement(__VLS_elements.a, __VLS_elements.a)({
    href: "/account",
});
__VLS_asFunctionalElement(__VLS_elements.button, __VLS_elements.button)({
    'aria-label': "Shopping cart",
});
__VLS_asFunctionalElement(__VLS_elements.main, __VLS_elements.main)({});
__VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
    ...{ class: "hero" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
__VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
__VLS_asFunctionalElement(__VLS_elements.h1, __VLS_elements.h1)({});
__VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
__VLS_asFunctionalElement(__VLS_elements.a, __VLS_elements.a)({
    href: "#catalog",
});
__VLS_asFunctionalElement(__VLS_elements.aside, __VLS_elements.aside)({});
__VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({});
__VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
__VLS_asFunctionalElement(__VLS_elements.br)({});
__VLS_asFunctionalElement(__VLS_elements.small, __VLS_elements.small)({});
__VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
    id: "catalog",
    ...{ class: "catalog" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "heading" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
__VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
__VLS_asFunctionalElement(__VLS_elements.h2, __VLS_elements.h2)({});
__VLS_asFunctionalElement(__VLS_elements.select, __VLS_elements.select)({
    ...{ onChange: (__VLS_ctx.store.loadProducts) },
    value: (__VLS_ctx.store.category),
});
// @ts-ignore
[store, store,];
__VLS_asFunctionalElement(__VLS_elements.option, __VLS_elements.option)({
    value: "",
});
for (const [category] of __VLS_getVForSourceType((__VLS_ctx.store.categories))) {
    // @ts-ignore
    [store,];
    __VLS_asFunctionalElement(__VLS_elements.option, __VLS_elements.option)({
        key: (category.id),
        value: (category.slug),
    });
    (category.name);
}
if (__VLS_ctx.store.loading) {
    // @ts-ignore
    [store,];
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({
        ...{ class: "state" },
    });
}
else if (__VLS_ctx.store.error) {
    // @ts-ignore
    [store,];
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({
        ...{ class: "state error" },
    });
    (__VLS_ctx.store.error);
    // @ts-ignore
    [store,];
}
else {
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "grid" },
    });
    for (const [product] of __VLS_getVForSourceType((__VLS_ctx.store.products))) {
        // @ts-ignore
        [store,];
        __VLS_asFunctionalElement(__VLS_elements.article, __VLS_elements.article)({
            key: (product.id),
            ...{ class: "product-card" },
        });
        __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
            ...{ class: "product-card__visual" },
        });
        if (product.images[0]) {
            __VLS_asFunctionalElement(__VLS_elements.img)({
                src: (product.images[0].image),
                alt: (product.images[0].alt_text || product.name),
                loading: "lazy",
                decoding: "async",
            });
        }
        else {
            __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
                ...{ class: "product-card__fallback" },
                'aria-hidden': "true",
            });
            __VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({});
            __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
            __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
        }
        __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({
            ...{ class: "product-card__seal" },
            'aria-hidden': "true",
        });
        __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
            ...{ class: "product-card__content" },
        });
        __VLS_asFunctionalElement(__VLS_elements.small, __VLS_elements.small)({
            ...{ class: "product-card__category" },
        });
        (product.category.name);
        __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
        (product.name);
        __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
        (product.short_description);
        __VLS_asFunctionalElement(__VLS_elements.footer, __VLS_elements.footer)({
            ...{ class: "product-card__footer" },
        });
        __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
        (product.price_cad);
        __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
        __VLS_asFunctionalElement(__VLS_elements.button, __VLS_elements.button)({
            type: "button",
            disabled: (!product.in_stock),
        });
        (product.in_stock ? "Add to bag" : "Sold out");
    }
}
__VLS_asFunctionalElement(__VLS_elements.footer, __VLS_elements.footer)({});
__VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
__VLS_asFunctionalElement(__VLS_elements.a, __VLS_elements.a)({
    href: "https://organicarchives.organicemperor.com",
});
__VLS_asFunctionalElement(__VLS_elements.a, __VLS_elements.a)({
    href: "/privacy",
});
__VLS_asFunctionalElement(__VLS_elements.a, __VLS_elements.a)({
    href: "/returns",
});
__VLS_asFunctionalElement(__VLS_elements.a, __VLS_elements.a)({
    href: "https://maaltech.pro",
});
/** @type {__VLS_StyleScopedClasses['announcement']} */ ;
/** @type {__VLS_StyleScopedClasses['brand']} */ ;
/** @type {__VLS_StyleScopedClasses['hero']} */ ;
/** @type {__VLS_StyleScopedClasses['catalog']} */ ;
/** @type {__VLS_StyleScopedClasses['heading']} */ ;
/** @type {__VLS_StyleScopedClasses['state']} */ ;
/** @type {__VLS_StyleScopedClasses['state']} */ ;
/** @type {__VLS_StyleScopedClasses['error']} */ ;
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__visual']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__fallback']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__seal']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__content']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__category']} */ ;
/** @type {__VLS_StyleScopedClasses['product-card__footer']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup: () => ({
        store: store,
        search: search,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
