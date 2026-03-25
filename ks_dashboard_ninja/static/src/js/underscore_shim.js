/** @odoo-module **/

// Minimal underscore-like shim to satisfy legacy code expecting `_`.
// Provides only the utilities used by this module.
(function () {
    if (window._) return; // Do not override if already present

    function values(obj) {
        return obj ? Object.values(obj) : [];
    }

    function keys(obj) {
        return obj ? Object.keys(obj) : [];
    }

    function each(list, iteratee) {
        if (!list || !iteratee) return;
        if (Array.isArray(list)) {
            list.forEach(function (val, idx) { iteratee(val, idx); });
        } else if (typeof list === 'object') {
            Object.keys(list).forEach(function (k) { iteratee(list[k], k); });
        }
    }

    function find(list, predicate) {
        if (!list || !predicate) return undefined;
        if (Array.isArray(list)) {
            return list.find(predicate);
        } else if (typeof list === 'object') {
            var ks;
            var vs = Object.keys(list);
            for (var i = 0; i < vs.length; i++) {
                ks = vs[i];
                if (predicate(list[ks], ks)) return list[ks];
            }
        }
        return undefined;
    }

    function extend(target) {
        target = target || {};
        for (var i = 1; i < arguments.length; i++) {
            var src = arguments[i] || {};
            Object.assign(target, src);
        }
        return target;
    }

    function wrapper(obj) {
        return {
            each: function (iter) { each(obj, iter); return this; },
            values: function () { return values(obj); },
            find: function (pred) { return find(obj, pred); },
            keys: function () { return keys(obj); },
        };
    }

    var underscoreShim = function (obj) { return wrapper(obj); };
    underscoreShim.values = values;
    underscoreShim.each = each;
    underscoreShim.find = find;
    underscoreShim.keys = keys;
    underscoreShim.extend = extend;

    window._ = underscoreShim;
})();
