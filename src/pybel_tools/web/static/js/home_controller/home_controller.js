$(document).ready(function () {

    // returns joined string with the properties of the selected elements in select2Element. Property can be the text or id
    function getSelection(select2Element, selectionProperty, joinBy) {

        var selectedElements = [];

        $.each(select2Element, function (index, value) {
            selectedElements.push(encodeURIComponent(value[selectionProperty]));
        });

        return selectedElements.join(joinBy)

    }

    $("#provenance_form").submit(function () {

        $("#pubmed_list").val(getSelection($("#pubmed_selection").select2("data"), "text", ","));

        $("#author_list").val(getSelection($("#author_selection").select2("data"), "text", ","));

    });

    $("#subgraph_form").submit(function () {

        $("#node_list").val(getSelection($("#node_selection").select2("data"), "id", ","));

    });

    $("#node_selection").select2({
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
    });

    $("#author_selection").select2({
        minimumInputLength: 2,
        multiple: true,
        placeholder: "Please type authors here",
        ajax: {
            url: function () {
                return "/api/suggestion/authors/";
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
    });

    $("#pubmed_selection").select2({
        minimumInputLength: 2,
        multiple: true,
        placeholder: "Please type PubMed Identifiers here",
        ajax: {
            url: function () {
                return "/api/suggestion/pubmed/";
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
    });
});
