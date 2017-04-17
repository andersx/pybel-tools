$(document).ready(function () {

    // Required for multiple autocompletion
    function splitByPipes(val) {
        return val.split(/\|/);
    }

    function splitByCommas(val) {
        return val.split(/,\s*/);
    }

    function extractLastCommas(term) {
        return splitByCommas(term).pop();
    }

    function extractLastPipes(term) {
        return splitByPipes(term).pop();
    }

    // LICENSE: http://www.devthought.com/projects/mootools/textboxlist/

    // Node autocompletion
    $("#node_list").autocomplete({

        source: function (request, response) {
            $.ajax({
                dataType: "json",
                contentType: "application/json; charset=utf-8",
                type: 'GET',
                url: "/api/suggestion/nodes/" + request.term,
                success: function (data) {
                    // Only gives the first 20 matches
                    response(data.slice(0, 20));
                }
            });
        },
        search: function () {
            // custom minLength
            var term = extractLastPipes(this.value);
            if (term.length < 1) {
                return false;
            }
        },
        focus: function () {
            // prevent value inserted on focus
            return false;
        },
        select: function (event, ui) {
            var terms = splitByPipes(this.value);
            // remove the current input
            terms.pop();
            // add the selected item
            terms.push(ui.item.value);
            // add placeholder to get the comma-and-space at the end
            terms.push("");
            this.value = terms.join("|");
            return false;
        },
        minLength: 2
    });

    // Author autocompletion
    $("#author_list").autocomplete({

        source: function (request, response) {
            $.ajax({
                dataType: "json",
                contentType: "application/json; charset=utf-8",
                type: 'GET',
                url: "/api/suggestion/authors/" + request.term,
                success: function (data) {
                    // Only gives the first 20 matches
                    response(data.slice(0, 20));
                }
            });
        },
        search: function () {
            // custom minLength
            var term = extractLastCommas(this.value);
            if (term.length < 1) {
                return false;
            }
        },
        focus: function () {
            // prevent value inserted on focus
            return false;
        },
        select: function (event, ui) {
            var terms = splitByCommas(this.value);
            // remove the current input
            terms.pop();
            // add the selected item
            terms.push(ui.item.value);
            // add placeholder to get the comma-and-space at the end
            terms.push("");
            this.value = terms.join(",");
            return false;
        },
        minLength: 2
    });

    // PubMed IDs autocompletion
    $("#pubmed_list").autocomplete({

        source: function (request, response) {
            $.ajax({
                dataType: "json",
                contentType: "application/json; charset=utf-8",
                type: 'GET',
                url: "/api/suggestion/pubmed/" + request.term,
                success: function (data) {
                    // Only gives the first 20 matches
                    response(data.slice(0, 20));
                }
            });
        },
        search: function () {
            // custom minLength
            var term = extractLastCommas(this.value);
            if (term.length < 1) {
                return false;
            }
        },
        focus: function () {
            // prevent value inserted on focus
            return false;
        },
        select: function (event, ui) {
            var terms = splitByCommas(this.value);
            // remove the current input
            terms.pop();
            // add the selected item
            terms.push(ui.item.value);
            // add placeholder to get the comma-and-space at the end
            terms.push("");
            this.value = terms.join(",");
            return false;
        },
        minLength: 2
    });


    $('#subgraph_form').submit(function (e) {

        var data = $("#node_selection").select2('data');

        var nodesIDs = [];

        $.each(data, function (index, value) {
            nodesIDs.push(value.id)
        });

        $("#node_list").val(nodesIDs.join("|"));

    });

    $("#node_selection").select2({
        // data:data
        minimumInputLength: 2,
        multiple: true,
        placeholder: 'Please type your nodes of interest here',
        ajax: {
            url: function (params) {
                return "/api/suggestion/nodes/";
            },
            type: "GET",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: function (params) {
                return {
                    search: params.term
                };
            },
            delay: 250,
            processResults: function (data) {
                return {
                    results: data.map(function (item) {
                            return {
                                id: item.id,
                                text: item.text
                            };
                        }
                    )
                };
            }
        }
    })


});
