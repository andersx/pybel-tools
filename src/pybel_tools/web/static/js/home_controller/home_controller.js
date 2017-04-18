$(document).ready(function () {

    $("#provenance_form").submit(function (e) {

        //TODO: MAKE ITS OWN FUNCTION

        var pubmedSelection = $("#pubmed_selection").select2("data");

        var pubmeds = [];

        $.each(pubmedSelection, function (index, value) {
            pubmeds.push(value.id)
        });

        $("#pubmed_list").val(pubmeds.join(","));

        var authorSelection = $("#author_selection").select2("data");

        var authors = [];

        $.each(authorSelection, function (index, value) {
            authors.push(value.text)
        });

        $("#author_list").val(authors.join(","));

    });

    $("#subgraph_form").submit(function (e) {

        var nodeSelection = $("#node_selection").select2("data");

        var nodesIDs = [];

        $.each(nodeSelection, function (index, value) {
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
