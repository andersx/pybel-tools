$(document).ready(function () {

    function getSelectionText(select2Element, joinBy) {
        //TODO switch to a logical filter
        var selectedElements = [];

        $.each(select2Element, function (index, value) {
            selectedElements.push(value.text);
        });

        return selectedElements.join(joinBy)

    }

    function getSelectionID(select2Element, joinBy) {
        //TODO switch to a logical filter?
        var selectedElements = [];

        $.each(select2Element, function (index, value) {
            selectedElements.push(encodeURIComponent(value.id));
        });

        return selectedElements.join(joinBy)

    }

    $("#provenance_form").submit(function (e) {

        $("#pubmed_list").val(getSelectionText($("#pubmed_selection").select2("data"), ","));

        $("#author_list").val(getSelectionText($("#author_selection").select2("data")), ",");

    });

    $("#subgraph_form").submit(function (e) {

        $("#node_list").val(getSelectionID($("#node_selection").select2("data")), ",");

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
        placeholder: "Please type authors here",
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
        placeholder: "Please type PubMed Identifiers here",
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
