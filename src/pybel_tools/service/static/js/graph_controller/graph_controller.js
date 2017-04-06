$(document).ready(function () {


    function renderEmptyFrame() {
        // Render empty rectangle

        d = document;
        e = d.documentElement;
        g = d.getElementsByTagName('body')[0];

        var graphDiv = $('#graph-chart');
        var w = graphDiv.width(), h = graphDiv.height();

        var svg = d3.select("#graph-chart").append("svg")
            .attr("width", w)
            .attr("height", h);

        // Background
        svg.append("rect")
            .attr("class", "background")
            .attr("width", "100%")
            .attr("height", "100%")
            .attr("fill", "#fcfbfb")
            .style("pointer-events", "all");

        svg.append("text")
            .attr("class", "title")
            .attr("x", w / 3.2)
            .attr("y", h / 2)
            .text("Please filter the graph by annotation and press submit");
    }

    function clearUsedDivs() {
        // Force div
        var graph_div = $('#graph-chart');
        // Node search div
        var node_panel = $('#node-list');
        // Edge search div
        var edge_panel = $('#edge-list');

        // Clean the current frame
        graph_div.empty();
        node_panel.empty();
        edge_panel.empty();
    }

    ///////////////////////////////////////
    /// Functions for updating the graph //
    ///////////////////////////////////////

    function savePreviousPositions() {
        // Save current positions into prevLoc 'object;
        var prevPos = {};

        // __data__ can be accessed also as an attribute (d.__data__)
        d3.selectAll(".node").data().map(function (d) {
            if (d) {
                prevPos[d.id] = [d.x, d.y];
            }

            return d;
        });

        return prevPos
    }

    function updateNodePosition(jsonData, prevPos) {

        var newNodesArray = [];

        // Set old locations back into the original nodes
        $.each(jsonData.nodes, function (index, value) {

            if (prevPos[value.id]) {

                oldX = prevPos[value.id][0];
                oldY = prevPos[value.id][1];
                // value.fx = oldX;
                // value.fy = oldY;
            } else {
                // If no previous coordinate... Start from off screen for a fun zoom-in effect
                oldX = -100;
                oldY = -100;
                newNodesArray.push(value.id);
            }

            value.x = oldX;
            value.y = oldY;

        });

        return {json: jsonData, new_nodes: newNodesArray}
    }

    function findDuplicates(data) {

        var hashMap = {};

        data.forEach(function (element, index) {

            if (!(element in hashMap)) {
                hashMap[element] = 0;
            }
            hashMap[element] += 1;
        });

        var duplicates = [];

        $.each(hashMap, function (key, value) {
            if (value > 1) {
                duplicates.push(key);
            }
        });

        return duplicates;
    }

    // Required for multiple autocompletion
    function split(val) {
        return val.split(/,\s*/);
    }

    /////////////////////////////
    // Filter tree annotations //
    /////////////////////////////

    function getSelectedNodesFromTree(tree) {
        var selectedNodes = tree.selected(true);

        var selectionHashMap = {};

        selectedNodes.forEach(function (node_object) {

            var key = node_object.text.toString();

            selectionHashMap[key] = node_object.children.map(function (child) {
                return child.text

            });
        });

        return selectionHashMap;
    }

    function parameterFilters() {
        var args = getSelectedNodesFromTree(tree);
        args["remove"] = window.deleteNodes.join();
        args["append"] = window.expandNodes.join();
        return args
    }

    var tree = new InspireTree({
        target: '#tree',
        selection: {
            mode: 'checkbox',
            multiple: true
        },
        data: window.filters
    });

    tree.on('model.loaded', function () {
        tree.expand();
    });

    // Render the empty frame
    renderEmptyFrame();

    $("#submit-button").on("click", function () {
        $.getJSON("/network/" + window.id + '?' + $.param(getSelectedNodesFromTree(tree), true), function (data) {
            initD3Force(data);
        });
    });


    ////////////////////////
    // Exporting funtions //
    ////////////////////////

    d3.select("#save-svg-graph")
        .on("click", downloadSvg);

    function downloadSvg() {
        try {
            var isFileSaverSupported = !!new Blob();
        } catch (e) {
            alert("blob not supported");
        }

        var html = d3.select("svg")
            .attr("title", "test2")
            .attr("version", 1.1)
            .attr("xmlns", "http://www.w3.org/2000/svg")
            .node().parentNode.innerHTML;

        var blob = new Blob([html], {type: "image/svg+xml"});
        saveAs(blob, "MyGraph.svg");
    };

    function downloadText(response, name) {
        var element = document.createElement('a');
        element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(response));
        element.setAttribute('download', name);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }

    // Export to BEL
    $("#bel-button").click(function () {
        $.ajax({
            url: '/network/' + window.id,
            dataType: "text",
            data: $.param(getSelectedNodesFromTree(tree), true) + '&format=bel'
        }).done(function (response) {
            downloadText(response, 'MyGraph.bel')
        });
    });

    // Export to GraphML
    $("#graphml-button").click(function () {
        window.location.href = '/network/' + window.id + '?' + $.param(getSelectedNodesFromTree(tree), true) + '&' + 'format=graphml';
    });

    // Export to bytes
    $("#bytes-button").click(function () {
        window.location.href = '/network/' + window.id + '?' + $.param(getSelectedNodesFromTree(tree), true) + '&' + 'format=bytes';

    });

    // Export to CX
    $("#cx-button").click(function () {
        window.location.href = '/network/' + window.id + '?' + $.param(getSelectedNodesFromTree(tree), true) + '&' + 'format=cx';
    });

    // Export to CSV
    $("#csv-button").click(function () {
        window.location.href = '/network/' + window.id + '?' + $.param(getSelectedNodesFromTree(tree), true) + '&' + 'format=csv';
    });


    // Initialize d3.js force to plot the networks from neo4j json
    function initD3Force(graph) {

        /////////////////////
        // d3-context-menu //
        /////////////////////

        // Definition of context menu
        var menu = [
            {
                title: 'Expand node',
                action: function (elm, d, i) {
                    // Variables explanation:
                    // elm: [object SVGGElement] d: [object Object] i: (#Number)

                    var positions = savePreviousPositions();

                    // Push selected node to expand node list
                    window.expandNodes.push(d.id);
                    var args = parameterFilters();

                    // Ajax to update the cypher query. Three list are sent to the server. pks of the subgraphs, list of nodes to delete and list of nodes to expand
                    $.ajax({
                        url: "/network/" + window.id,
                        dataType: "json",
                        data: $.param(args, true)
                    }).done(function (response) {

                        // Load new data, first empty all created divs and clear the current network
                        var data = updateNodePosition(response, positions);

                        clearUsedDivs();

                        initD3Force(data['json']);

                    });
                },
                disabled: false // optional, defaults to false
            },
            {
                title: 'Delete node',
                action: function (elm, d, i) {

                    var positions = savePreviousPositions();

                    // Push selected node to delete node list
                    window.deleteNodes.push(d.id);
                    var args = parameterFilters();


                    $.ajax({
                        url: "/network/" + window.id,
                        dataType: "json",
                        data: $.param(args, true)
                    }).done(function (response) {

                        // Load new data, first empty all created divs and clear the current network
                        var data = updateNodePosition(response, positions);

                        clearUsedDivs();

                        initD3Force(data['json']);
                    });

                }
            },
        ];

        //////////////////////////////
        // Main graph visualization //
        //////////////////////////////

        // Enable nodes and edges tabs
        $(".disabled").attr('class', 'nav-link ');

        // Force div
        var graphDiv = $('#graph-chart');
        // Node search div
        var node_panel = $('#node-list');
        // Edge search div
        var edge_panel = $('#edge-list');

        clearUsedDivs();

        d = document;
        e = d.documentElement;
        g = d.getElementsByTagName('body')[0];

        var w = graphDiv.width(), h = graphDiv.height();

        var focusNode = null, highlightNode = null;

        // Highlight color variables

        // Highlight color of the node boundering
        var highlightNodeBoundering = "#4EB2D4";

        // Highlight color of the edge
        var highlightedLinkColor = "#4EB2D4";

        // Text highlight color
        var highlightText = "#4EB2D4";

        // Size when zooming scale
        var size = d3.scalePow().exponent(1)
            .domain([1, 100])
            .range([8, 24]);

        // Simulation parameters
        var linkDistance = 100, fCharge = -1000, linkStrength = 0.7, collideStrength = 1;

        // Simulation defined with variables
        var simulation = d3.forceSimulation()
            .force("link", d3.forceLink()
                .distance(linkDistance)
                .strength(linkStrength)
            )
            .force("collide", d3.forceCollide()
                .radius(function (d) {
                    return d.r + 10
                })
                .strength(collideStrength)
            )
            .force("charge", d3.forceManyBody()
                .strength(fCharge)
            )
            .force("center", d3.forceCenter(w / 2, h / 2))
            .force("y", d3.forceY(0))
            .force("x", d3.forceX(0));

        // Pin down functionality
        var nodeDrag = d3.drag()
            .on("start", dragStarted)
            .on("drag", dragged)
            .on("end", dragEnded);

        function dragStarted(d) {
            if (!d3.event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(d) {
            d.fx = d3.event.x;
            d.fy = d3.event.y;
        }

        function dragEnded(d) {
            if (!d3.event.active) simulation.alphaTarget(0);
        }

        function releaseNode(d) {
            d.fx = null;
            d.fy = null;
        }

        //END Pin down functionality

        var circleColor = "black";
        var defaultLinkColor = "#888";

        var nominalBaseNodeSize = 8;

        var nominalStroke = 1.5;
        // Zoom variables
        var minZoom = 0.1, maxZoom = 10;
        var border = 1, bordercolor = 'black';

        var svg = d3.select("#graph-chart").append("svg")
            .attr("width", w)
            .attr("height", h);

        // // Create definition for arrowhead.
        svg.append("defs").append("marker")
            .attr("id", "arrowhead")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 20)
            .attr("refY", 0)
            .attr("markerUnits", "strokeWidth")
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5");

        // // Create definition for stub.
        svg.append("defs").append("marker")
            .attr("id", "stub")
            .attr("viewBox", "-1 -5 2 10")
            .attr("refX", 15)
            .attr("refY", 0)
            .attr("markerUnits", "strokeWidth")
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M 0,0 m -1,-5 L 1,-5 L 1,5 L -1,5 Z");

        // Background
        svg.append("rect")
            .attr("width", "100%")
            .attr("height", "100%")
            .attr("fill", "#fcfbfb")
            .style("pointer-events", "all")
            // Zoom + panning functionality
            .call(d3.zoom()
                .scaleExtent([minZoom, maxZoom])
                .on("zoom", zoomed))
            .on("dblclick.zoom", null);


        function zoomed() {
            g.attr("transform", d3.event.transform);
        }

        // Border
        svg.append("rect")
            .attr("height", h)
            .attr("width", w)
            .style("stroke", bordercolor)
            .style("fill", "none")
            .style("stroke-width", border);

        // g = svg object where the graph will be appended
        var g = svg.append("g");

        var linkedByIndex = {};
        graph.links.forEach(function (d) {
            linkedByIndex[d.source + "," + d.target] = true;
        });

        function isConnected(a, b) {
            return linkedByIndex[a.index + "," + b.index] || linkedByIndex[b.index + "," + a.index] || a.index == b.index;
        }

        function ticked() {
            link
                .attr("x1", function (d) {
                    return d.source.x;
                })
                .attr("y1", function (d) {
                    return d.source.y;
                })
                .attr("x2", function (d) {
                    return d.target.x;
                })
                .attr("y2", function (d) {
                    return d.target.y;
                });

            node
                .attr("transform", function (d) {
                    return "translate(" + d.x + ", " + d.y + ")";
                });
        }


        simulation
            .nodes(graph.nodes)
            .on("tick", ticked);

        simulation.force("link")
            .links(graph.links);

        // Definition of links nodes text...

        var link = g.selectAll(".link")
            .data(graph.links)
            .enter().append("line")
            .style("stroke-width", nominalStroke)
            .style("stroke", defaultLinkColor)
            .on("mouseover", function (d) {
                setTimeout(function () {
                    displayEdgeInfo(d);
                }, 3000);
            })
            .attr("class", function (d) {
                if (['decreases', 'directlyDecreases', 'increases', 'directlyIncreases', 'negativeCorrelation',
                        'positiveCorrelation'].indexOf(d.relation) >= 0) {
                    return "link link_continuous"
                }
                else {
                    return "link link_dashed"
                }
            })
            .attr("marker-start", function (d) {
                if ('positiveCorrelation' == d.relation) {
                    return "url(#arrowhead)"
                }
                else if ('negativeCorrelation' == d.relation) {
                    return "url(#stub)"
                }
                else {
                    return ""
                }
            })
            .attr("marker-end", function (d) {
                if (['increases', 'directlyIncreases', 'positiveCorrelation'].indexOf(d.relation) >= 0) {
                    return "url(#arrowhead)"
                }
                else if (['decreases', 'directlyDecreases', 'negativeCorrelation'].indexOf(d.relation) >= 0) {
                    return "url(#stub)"
                }
                else {
                    return ""
                }
            });

        var node = g.selectAll(".nodes")
            .data(graph.nodes)
            .enter().append("g")
            .attr("class", "node")
            // Next two lines -> Pin down functionality
            .on('dblclick', releaseNode)
            // Box info
            .on("mouseover", function (d) {
                setTimeout(function () {
                    displayNodeInfo(d);
                }, 1000);
            })
            // context-menu on right click
            .on('contextmenu', d3.contextMenu(menu)) // Attach context menu to node's circle
            // Dragging
            .call(nodeDrag);

        var circle = node.append("path")
            .attr("d", d3.symbol()
                .size(function (d) {
                    return Math.PI * Math.pow(size(d.size) || nominalBaseNodeSize, 2);
                })
            )
            .attr("class", function (d) {
                return d.function
            })
            .style("stroke-width", nominalStroke)
            .style("stroke", circleColor);

        var text = node.append("text")
            .attr("class", "node-name")
            // .attr("id", nodehashes[d])
            .attr("fill", "black")
            .attr("dx", 12)
            .attr("dy", ".35em")
            .text(function (d) {
                return d.cname
            });

        // Highlight on mouseenter and back to normal on mouseout
        node.on("mouseenter", function (d) {
            setHighlight(d);
        })
            .on("mousedown", function () {
                d3.event.stopPropagation();
            }).on("mouseout", function () {
            exitHighlight();
        });

        function exitHighlight() {
            highlightNode = null;
            if (focusNode === null) {
                if (highlightNodeBoundering != circleColor) {
                    circle.style("stroke", circleColor);
                    text.style("fill", "black");
                    link.style("stroke", defaultLinkColor);
                }
            }
        }

        function setHighlight(d) {
            if (focusNode !== null) d = focusNode;
            highlightNode = d;

            if (highlightNodeBoundering != circleColor) {
                circle.style("stroke", function (o) {
                    return isConnected(d, o) ? highlightNodeBoundering : circleColor;
                });
                text.style("fill", function (o) {
                    return isConnected(d, o) ? highlightText : "black";
                });
                link.style("stroke", function (o) {
                    // All links connected to the node you hover on
                    return o.source.index == d.index || o.target.index == d.index ? highlightedLinkColor : defaultLinkColor;
                });
            }
        }

        // Highlight links on mouseenter and back to normal on mouseout
        link.on("mouseenter", function (d) {
            link.style("stroke", function (o) {
                // Specifically the link you hover on
                return o.source.index == d.source.index && o.target.index == d.target.index ? highlightedLinkColor : defaultLinkColor;
            });
        })
            .on("mousedown", function () {
                d3.event.stopPropagation();
            }).on("mouseout", function () {
            link.style("stroke", defaultLinkColor);
        });

        // Box info in table

        function displayNodeInfo(node) {
            $("#table-11").html("Node");
            $("#table-12").html(node.cname);
            $("#table-21").html("Function");
            $("#table-22").html(node.function);
            $("#table-31").html("Namespace");
            $("#table-32").html(node.namespace);
            $("#table-41").html("Name");
            $("#table-42").html(node.name);
        }


        function displayEdgeInfo(edge) {

            $("#table-11").html("Evidence");
            $("#table-12").html(edge.evidence);
            $("#table-21").html("Citation");
            $("#table-22").html("<a href=https://www.ncbi.nlm.nih.gov/pubmed/" + edge.citation.reference + " target='_blank' " +
                "style='color: blue; text-decoration: underline'>" + edge.citation.reference + "</a>");
            $("#table-31").html("Relation");
            $("#table-32").html(edge.relation);
            $("#table-41").html("Annotations");
            // Objects to string represented as JSON {key-value pairs}
            $("#table-42").html(JSON.stringify(edge.annotations));
        }


        // Freeze the graph when space is pressed
        function freezeGraph() {
            // Space button Triggers STOP
            if (d3.event.keyCode == 32) {
                simulation.stop();
            }
        }

        // Search functionality to check if array exists in an array of arrays
        function searchForArray(haystack, needle) {
            var i, j, current;
            for (i = 0; i < haystack.length; ++i) {
                if (needle.length === haystack[i].length) {
                    current = haystack[i];
                    for (j = 0; j < needle.length && needle[j] === current[j]; ++j);
                    if (j === needle.length)
                        return i;
                }
            }
            return -1;
        }

        // Filter nodes in list
        function nodesNotInArray(node_list) {
            var nodesNotInArray = svg.selectAll(".node").filter(function (el) {
                return node_list.indexOf(el.id) < 0;
            });
            return nodesNotInArray
        }


        function resetAttributesDoubleClick() {

            // On double click reset attributes (Important disabling the zoom behavior of dbl click because it interferes with this)
            svg.on("dblclick", function () {
                // SET default color
                svg.selectAll(".link").style("stroke", defaultLinkColor);
                // SET default attributes //
                svg.selectAll(".link, .node").style("visibility", "visible")
                    .style("opacity", "1");
                // Show node names
                svg.selectAll(".node-name").style("visibility", "visible").style("opacity", "1");
            });

        }

        function resetAttributes() {
            // Reset visibility and opacity
            svg.selectAll(".link, .node").style("visibility", "visible").style("opacity", "1");
            // Show node names
            svg.selectAll(".node-name").style("visibility", "visible").style("opacity", "1");
            svg.selectAll(".node-name").style("display", "block");

        }

        function hideNodesText(nodeList, visualization) {
            // Filter the text to those not belonging to the list of node names

            var nodesNotInList = g.selectAll(".node-name").filter(function (d) {
                return nodeList.indexOf(d.id) < 0;
            });

            if (visualization != true) {
                //noinspection JSDuplicatedDeclaration
                var visualizationOption = "opacity", on = "1", off = "0.1";
            } else {
                //noinspection JSDuplicatedDeclaration
                var visualizationOption = "visibility", on = "visible", off = "hidden";
            }

            // Change display property to 'none'
            $.each(nodesNotInList._groups[0], function (index, value) {
                value.style.setProperty(visualizationOption, off);
            });
        }

        function hideNodesTextInPaths(data, visualization) {

            // Array with all nodes in all paths
            var nodesInPaths = [];

            $.each(data, function (index, value) {
                $.each(value, function (index, value) {
                    nodesInPaths.push(value);
                });
            });

            // Filter the text whose innerHTML is not belonging to the list of nodeIDs
            var textNotInPaths = g.selectAll(".node-name").filter(function (d) {
                return nodesInPaths.indexOf(d.id) < 0;
            });

            if (visualization != true) {
                //noinspection JSDuplicatedDeclaration
                var visualizationOption = "opacity", on = "1", off = "0.1";
            } else {
                //noinspection JSDuplicatedDeclaration
                var visualizationOption = "visibility", on = "visible", off = "hidden";
            }

            // Change display property to 'none'
            $.each(textNotInPaths._groups[0], function (index, value) {
                value.style.setProperty(visualizationOption, off);
            });
        }

        function highlightEdges(edge_array) {

            // Array with names of the nodes in the selected edge
            var nodesInEdges = [];

            // Filtered not selected links
            var edgesNotInArray = g.selectAll(".link").filter(function (edgeObject) {

                if (edge_array.indexOf(edgeObject.source.cname + " " + edgeObject.relation + " " + edgeObject.target.cname) >= 0) {
                    nodesInEdges.push(edgeObject.source.cname);
                    nodesInEdges.push(edgeObject.target.cname);
                }
                else return edgeObject;
            });

            hideNodesText(nodesInEdges, false);

            var nodesNotInEdges = node.filter(function (node_object) {
                return nodesInEdges.indexOf(node_object.cname) < 0;
            });

            nodesNotInEdges.style("opacity", "0.1");
            edgesNotInArray.style("opacity", "0.1");

        }

        // Highlight nodes from array of ids and change the opacity of the rest of nodes
        function highlightNodes(nodeArray) {

            hideNodesText(nodeArray, false);

            // Filter not mapped nodes to change opacity
            var nodesNotInArray = svg.selectAll(".node").filter(function (el) {
                return searchForArray(nodeArray, el.cname) < 0;
            });

            // Not mapped links
            var notMappedEdges = g.selectAll(".link").filter(function (el) {
                // Source and target should be present in the edge
                return !((searchForArray(nodeArray, el.source.cname) >= 0 || searchForArray(nodeArray, el.target.cname) >= 0));
            });

            nodesNotInArray.style("opacity", "0.1");
            notMappedEdges.style("opacity", "0.1");
        }

        function colorPaths(data, visualization) {

            /**
             * Returns a random integer between min (inclusive) and max (inclusive)
             * Using Math.round() will give you a non-uniform distribution!
             */
            function getRandomInt(min, max) {
                return Math.floor(Math.random() * (max - min + 1)) + min;
            }

            // data: nested array with all nodes in each path
            // visualization: parameter with visualization info ('hide' || 'opaque)

            var link = g.selectAll(".link");

            ///////// Filter the nodes ////////

            // Array with all nodes in all paths
            var nodesInPaths = [];

            $.each(data, function (index, value) {
                $.each(value, function (index, value) {
                    nodesInPaths.push(value);
                });
            });

            // Filtering the nodes that are not in any of the paths
            var nodesNotInPaths = svg.selectAll(".node").filter(function (el) {
                return nodesInPaths.indexOf(el.id) < 0;
            });

            if (visualization != true) {
                //noinspection JSDuplicatedDeclaration
                var visualizationOption = "opacity", on = "1", off = "0.1";
            } else {
                //noinspection JSDuplicatedDeclaration
                var visualizationOption = "visibility", on = "visible", off = "hidden";
            }
            nodesNotInPaths.style(visualizationOption, off);

            ///////// Colour links in each path differently and hide others ////////

            // Colour the links ( Max 21 paths )
            var color_list = ['#ff2200', ' #282040', ' #a68d7c', ' #332b1a', ' #435916', ' #00add9', ' #bfd0ff', ' #f200c2',
                ' #990014', ' #d97b6c', ' #ff8800', ' #f2ffbf', ' #e5c339', ' #5ba629', ' #005947', ' #005580', ' #090040',
                ' #8d36d9', ' #e5005c', ' #733941', ' #993d00', ' #80ffb2', ' #66421a', ' #e2f200', ' #20f200', ' #80fff6',
                ' #002b40', ' #6e698c', ' #802079', ' #330014', ' #331400', ' #ffc480', ' #7ca682', ' #264a4d', ' #0074d9',
                ' #220080', ' #d9a3d5', ' #f279aa'];

            // iter = number of paths ( Max 21 paths )
            if (data.length > color_list.length) {
                //noinspection JSDuplicatedDeclaration
                var iter = color_list.length;
            } else {
                //noinspection JSDuplicatedDeclaration
                var iter = data.length;
            }

            // First hide or set to opacity 0.1 all links
            link.style(visualizationOption, off);

            // Make visible again all the edges that are in any of the paths
            var edgesInPaths = [];

            for (var x = 0; x < iter; x++) {

                // Push the array (each path) to a new one where all paths are stored
                var path = link.filter(function (el) {
                    // Source and target should be present in the edge and the distance in the array should be one
                    return ((data[x].indexOf(el.source.id) >= 0 && data[x].indexOf(el.target.id) >= 0)
                    && (Math.abs(data[x].indexOf(el.source.id) - data[x].indexOf(el.target.id)) == 1));
                });

                edgesInPaths.push(path);
            }

            // Only the links that are in any of the paths are visible
            for (var j = 0, len = edgesInPaths.length; j < len; j++) {
                edgesInPaths[j].style(visualizationOption, on);
            }

            // For each path give a different color
            for (var i = 0; i < iter; i++) {
                var edgesInPath = link.filter(function (el) {
                    // Source and target should be present in the edge and the distance in the array should be one
                    return ((data[i].indexOf(el.source.id) >= 0 && data[i].indexOf(el.target.id) >= 0)
                    && (Math.abs(data[i].indexOf(el.source.id) - data[i].indexOf(el.target.id)) == 1));
                });

                // Select randomly a color and apply to this path
                edgesInPath.style("stroke", color_list[getRandomInt(0, 21)]);
            }

        }

        // Call freezeGraph when a key is pressed, freezeGraph checks whether this key is "Space" that triggers the freeze
        d3.select(window).on("keydown", freezeGraph);

        /////////////////////////
        // Additional features //
        /////////////////////////

        function downloadLink(response, name) {
            var element = document.createElement('a');
            element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(response));
            element.setAttribute('download', name);
            element.style.display = 'none';
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
        }

        /////////////////////////////////////////////////////////////////////////
        // Build the node selection toggle and creates hashmap nodeNames to IDs /
        /////////////////////////////////////////////////////////////////////////

        // Build the node unordered list
        node_panel.append("<ul id='node-list-ul' class='list-group checked-list-box not-rounded'></ul>");

        // Variable with all node names
        var nodeNames = [];

        // Create node list and create an array with duplicates
        $.each(graph.nodes, function (key, value) {

            nodeNames.push(value.cname);

            $("#node-list-ul").append("<li class='list-group-item'><input class='node-checkbox' type='checkbox'><div class='node-checkbox " + value.function + "'></div><span class>" + value.cname + "</span></li>");
        });

        var duplicates = findDuplicates(nodeNames);

        var nodeNamesToId = {};

        // Check over duplicate cnames and create hashmap to id
        $.each(graph.nodes, function (key, value) {
            // if the node has no duplicate show it in autocompletion with its cname
            if (duplicates.indexOf(value.cname) < 0) {
                nodeNamesToId[value.cname] = value.id;
            }
            // if it has a duplicate show also the function after the cname
            else {
                nodeNamesToId[value.cname + ' (' + value.function + ')'] = value.id;
            }
        });

        // Highlight only selected nodes in the graph
        $('#get-checked-nodes').on('click', function (event) {
            event.preventDefault();
            var checkedItems = [];
            $(".node-checkbox:checked").each(function (idx, li) {
                checkedItems.push(li.parentElement.childNodes[2].innerHTML);
            });

            resetAttributes();
            highlightNodes(checkedItems);
            resetAttributesDoubleClick();

        });

        ///////////////////////////////////////
        // Build the edge selection toggle
        ///////////////////////////////////////


        // Build the node unordered list
        edge_panel.append("<ul id='edge-list-ul' class='list-group checked-list-box not-rounded'></ul>");


        $.each(graph.links, function (key, value_array) {

            $("#edge-list-ul").append("<li class='list-group-item'><input class='node-checkbox' type='checkbox'><span class>" +
                value_array.source.cname + ' ' + value_array.relation + ' ' + value_array.target.cname + "</span></li>");

        });

        $('#get-checked-edges').on('click', function (event) {
            event.preventDefault();

            var checkedItems = [];
            $(".node-checkbox:checked").each(function (idx, li) {
                checkedItems.push(li.parentElement.childNodes[1].innerHTML);
            });

            resetAttributes();

            highlightEdges(checkedItems);

            resetAttributesDoubleClick()
        });

        var shortestPathForm = $("#shortest-path-form");

        // Get the shortest path between two nodes via Ajax or get the BEL for the shortest path
        $('#button-shortest-path').on('click', function () {
            if (shortestPathForm.valid()) {

                var checkbox = shortestPathForm.find('input[name="visualization-options"]').is(":checked");

                var args = parameterFilters();
                args["source"] = nodeNamesToId[shortestPathForm.find('input[name="source"]').val()];
                args["target"] = nodeNamesToId[shortestPathForm.find('input[name="target"]').val()];

                var undirected = shortestPathForm.find('input[name="undirectionalize"]').is(":checked");

                if (undirected) {
                    args["undirected"] = undirected;
                }

                $.ajax({
                    url: '/paths/shortest/' + window.id,
                    type: shortestPathForm.attr('method'),
                    dataType: 'json',
                    data: $.param(args, true),
                    success: function (shortestPathNodes) {

                        // Change style in force
                        resetAttributes();

                        var nodesNotInPath = nodesNotInArray(shortestPathNodes);

                        var edgesNotInPath = g.selectAll(".link").filter(function (el) {
                            // Source and target should be present in the edge and the distance in the array should be one
                            return !((shortestPathNodes.indexOf(el.source.id) >= 0 && shortestPathNodes.indexOf(el.target.id) >= 0)
                            && (Math.abs(shortestPathNodes.indexOf(el.source.id) - shortestPathNodes.indexOf(el.target.id)) == 1));
                        });

                        // If checkbox is True -> Hide all, Else -> Opacity 0.1
                        if (checkbox == true) {
                            nodesNotInPath.style("visibility", "hidden");
                            edgesNotInPath.style("visibility", "hidden");
                        } else {
                            nodesNotInPath.style("opacity", "0.1");
                            edgesNotInPath.style("opacity", "0.05");
                        }
                        hideNodesText(shortestPathNodes, checkbox);
                        resetAttributesDoubleClick();
                    }, error: function (request) {
                        alert(request.responseText);
                    }
                })
            }
        });

        // Shortest path validation form
        shortestPathForm.validate(
            {
                rules: {
                    source: {
                        required: true,
                        minlength: 2
                    },
                    target: {
                        required: true,
                        minlength: 2
                    }
                },
                messages: {
                    source: "Please enter a valid source",
                    target: "Please enter a valid target"
                }
            }
        );

        // Get or show all paths between two nodes via Ajax

        var all_path_form = $("#all-paths-form");

        $('#button-all-paths').on('click', function () {
            if (all_path_form.valid()) {

                var checkbox = all_path_form.find('input[name="visualization-options"]').is(":checked");

                var args = parameterFilters();
                args["source"] = nodeNamesToId[all_path_form.find('input[name="source"]').val()];
                args["target"] = nodeNamesToId[all_path_form.find('input[name="target"]').val()];

                var undirected = all_path_form.find('input[name="undirectionalize"]').is(":checked");

                if (undirected) {
                    args["undirected"] = undirected;
                }

                $.ajax({
                    url: '/paths/all/' + window.id,
                    type: all_path_form.attr('method'),
                    dataType: 'json',
                    data: $.param(args, true),
                    success: function (data) {

                        if (data.length == 0) {
                            alert('No paths between the selected nodes');
                        }

                        resetAttributes();

                        // Apply changes in style for select paths
                        hideNodesTextInPaths(data, false);
                        colorPaths(data, checkbox);
                        resetAttributesDoubleClick()
                    },
                    error: function (request) {
                        alert(request.responseText);
                    }
                })
            }
        });

        all_path_form.validate(
            {
                rules: {
                    source: {
                        required: true,
                        minlength: 2
                    },
                    target: {
                        required: true,
                        minlength: 2
                    }
                },
                messages: {
                    source: "Please enter a valid source",
                    target: "Please enter a valid target"
                }
            }
        );

        // Shortest path autocompletion input
        var nodeNames = Object.keys(nodeNamesToId).sort();

        $("#source-node").autocomplete({
            source: nodeNames,
            appendTo: "#paths"
        });

        $("#target-node").autocomplete({
            source: nodeNames,
            appendTo: "#paths"
        });

        // All paths form autocompletion
        $("#source-node2").autocomplete({
            source: nodeNames,
            appendTo: "#paths"
        });

        $("#target-node2").autocomplete({
            source: nodeNames,
            appendTo: "#paths"
        });

        // Update Node Dropdown
        $("#node-search").on("keyup", function () {
            // Get value from search form (fixing spaces and case insensitive
            var searchText = $(this).val();
            searchText = searchText.toLowerCase();
            searchText = searchText.replace(/\s+/g, '');

            $.each($('#node-list-ul')[0].childNodes, updateNodeArray);
            function updateNodeArray() {
                var currentLiText = $(this).find("span")[0].innerHTML,
                    showCurrentLi = ((currentLiText.toLowerCase()).replace(/\s+/g, '')).indexOf(searchText) !== -1;
                $(this).toggle(showCurrentLi);
            }
        });

        // Update Edge Dropdown
        $("#edge-search").on("keyup", function () {
            // Get value from search form (fixing spaces and case insensitive
            var searchText = $(this).val();
            searchText = searchText.toLowerCase();
            searchText = searchText.replace(/\s+/g, '');

            $.each($('#edge-list-ul')[0].childNodes, updateEdgeArray);
            function updateEdgeArray() {

                var currentLiText = $(this).find("span")[0].innerHTML,
                    showCurrentLi = ((currentLiText.toLowerCase()).replace(/\s+/g, '')).indexOf(searchText) !== -1;
                $(this).toggle(showCurrentLi);
            }
        });


        // Get or show all paths between two nodes via Ajax

        var betwenness_form = $("#betweenness-centrality");

        $('#betweenness-button').on('click', function () {
            if (betwenness_form.valid()) {

                var checkbox = all_path_form.find('input[name="visualization-options"]').is(":checked");

                var args = parameterFilters();
                args["source"] = nodeNamesToId[all_path_form.find('input[name="source"]').val()];
                args["target"] = nodeNamesToId[all_path_form.find('input[name="target"]').val()];

                var undirected = all_path_form.find('input[name="undirectionalize"]').is(":checked");

                if (undirected) {
                    args["undirected"] = undirected;
                }

                $.ajax({
                    url: '/paths/all/' + window.id,
                    type: all_path_form.attr('method'),
                    dataType: 'json',
                    data: $.param(args, true),
                    success: function (data) {

                        if (data.length == 0) {
                            alert('No paths between the selected nodes');
                        }

                        resetAttributes();

                        // Apply changes in style for select paths
                        hideNodesTextInPaths(data, false);
                        colorPaths(data, checkbox);
                        resetAttributesDoubleClick()
                    },
                    error: function (request) {
                        alert(request.responseText);
                    }
                })
            }
        });

        betwenness_form.validate(
            {
                rules: {
                    betweenness: {
                        required: true,
                        digits: true
                    }
                },
                messages: {
                    betweenness: "Please enter a valid source",
                }
            }
        );

        // Hide text in graph
        $("#hide_node_names").on("click", function () {
            svg.selectAll(".node-name").style("display", "none");
        });

        // Hide text in graph
        $("#restore_node_names").on("click", function () {
            svg.selectAll(".node-name").style("display", "block");
        });

        // Hide text in graph
        $("#restore").on("click", function () {
            resetAttributes();
        });
    }


});
