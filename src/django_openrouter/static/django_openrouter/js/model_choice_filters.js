"use strict";
{
    const $ = django.jQuery;
    const GROUP_ID = "fallback_links-group";

    function filterParams() {
        return {
            price: document.getElementById("or-model-price-filter")?.value || "",
            speed: document.getElementById("or-model-speed-filter")?.value || "",
        };
    }

    function patchSelect2() {
        $.fn.djangoAdminSelect2 = function () {
            $.each(this, function (_i, element) {
                $(element).select2({
                    ajax: {
                        data: (params) => ({
                            term: params.term,
                            page: params.page,
                            app_label: element.dataset.appLabel,
                            model_name: element.dataset.modelName,
                            field_name: element.dataset.fieldName,
                            ...filterParams(),
                        }),
                    },
                    width: "100%",
                });
            });
            return this;
        };
    }

    function injectFilters(group) {
        if (group.querySelector(".or-model-filters")) {
            return;
        }
        const bar = document.createElement("div");
        bar.className = "or-model-filters";
        bar.innerHTML = `
            <span>
                <label for="or-model-price-filter">Price</label>
                <select id="or-model-price-filter">
                    <option value="">All</option>
                    <option value="free">Free</option>
                    <option value="cheap">Cheap (&lt; $1 / 1M)</option>
                    <option value="mid">Mid ($1-$10 / 1M)</option>
                    <option value="expensive">Expensive (>= $10 / 1M)</option>
                </select>
            </span>
            <span>
                <label for="or-model-speed-filter">Speed</label>
                <select id="or-model-speed-filter">
                    <option value="">All</option>
                    <option value="fast">Fast (&lt; 400 ms)</option>
                    <option value="medium">Medium (400-1200 ms)</option>
                    <option value="slow">Slow (>= 1200 ms)</option>
                    <option value="unknown">Unknown latency</option>
                </select>
            </span>
        `;
        const heading = group.querySelector("h2");
        if (heading && heading.nextSibling) {
            heading.parentNode.insertBefore(bar, heading.nextSibling);
        } else {
            group.prepend(bar);
        }
    }

    function rebindAutocomplete(root) {
        const $fields = $(root).find(".admin-autocomplete").not("[name*=__prefix__]");
        $fields.each(function () {
            if ($(this).hasClass("select2-hidden-accessible")) {
                $(this).select2("destroy");
            }
        });
        $fields.djangoAdminSelect2();
    }

    document.addEventListener("DOMContentLoaded", () => {
        const group = document.getElementById(GROUP_ID);
        if (!group || typeof $.fn.djangoAdminSelect2 !== "function") {
            return;
        }
        injectFilters(group);
        patchSelect2();
        rebindAutocomplete(group);
        document.addEventListener("formset:added", (event) => {
            $(event.target).find(".admin-autocomplete").djangoAdminSelect2();
        });
    });
}
