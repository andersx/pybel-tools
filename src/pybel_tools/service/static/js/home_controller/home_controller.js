/**
 * Created by ddomingofernandez on 4/7/17.
 */


$(document).ready(function () {

    // Required for multiple autocompletion
    function split(val) {
        return val.split(/,\s*/);
    }

    function extractLast(term) {
        return split(term).pop();
    }

    $("#node-input").autocomplete({

        source: function (request, response) {
            $.ajax({
                dataType: "json",
                contentType: "application/json; charset=utf-8",
                type: 'GET',
                url: "/api/nodes/suggestion/" + request.term,
                success: function (data) {
                    // Only gives the first 20 matches
                    response(data.slice(0, 20));
                }
            });
        },
        search: function () {
            // custom minLength
            var term = extractLast(this.value);
            if (term.length < 1) {
                return false;
            }
        },
        focus: function () {
            // prevent value inserted on focus
            return false;
        },
        select: function (event, ui) {
            var terms = split(this.value);
            // remove the current input
            terms.pop();
            // add the selected item
            terms.push(ui.item.value);
            // add placeholder to get the comma-and-space at the end
            terms.push("");
            this.value = terms.join(", ");
            return false;
        },
        minLength: 2
    });
});
