$(document).ready(function () {

    function getSelectionData(select2Element, joinBy) {

        var selectedElements = [];

        $.each(select2Element, function (index, value) {
            selectedElements.push(encodeURIComponent(value.text));
        });

        return selectedElements.join(joinBy)

    }

    $("#provenance_form").submit(function (e) {

        $("#pubmed_list").val(getSelectionData($("#pubmed_selection").select2("data"), ","));

        $("#author_list").val($("#author_selection").select2("data"), ",");

    });

    $("#subgraph_form").submit(function (e) {

        $("#node_list").val($("#node_selection").select2("data"), "|");

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
    });

    $("#author_selection").select2({
        minimumInputLength: 2,
        multiple: true,
        placeholder: "Please type here authors",
        ajax: {
            url: function (params) {
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
        placeholder: "Please type here your PubMeds",
        ajax: {
            url: function (params) {
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
