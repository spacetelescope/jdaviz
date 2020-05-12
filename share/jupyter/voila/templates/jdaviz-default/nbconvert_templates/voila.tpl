<!DOCTYPE html>
<html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/vue/2.6.10/vue.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/vuetify/2.2.6/vuetify.min.js"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/vuetify/2.2.6/vuetify.min.css" rel="stylesheet">
        <link href='https://fonts.googleapis.com/css?family=Roboto:100,300,400,500,700,900|Material+Icons' rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/@mdi/font@4.x/css/materialdesignicons.min.css" rel="stylesheet">
        <link href='{{resources.base_url}}voila/static/index.css' rel="stylesheet">
        <link href='{{resources.base_url}}voila/static/theme-light.css' rel="stylesheet">
        <script src="{{resources.base_url}}voila/static/require.min.js" integrity="sha256-Ae2Vz/4ePdIu6ZyI/5ZGsYnb+m0JlOmKPjt6XZ9JJkA=" crossorigin="anonymous"></script>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, minimal-ui">
    </head>

    <body data-base-url="{{resources.base_url}}voila/">
        <script>
            {% include "util.js" %}
        </script>

        {% include "app.html" %}
    </body>
{%- set kernel_id = kernel_start() -%}
    <script id="jupyter-config-data" type="application/json">
        {
          "baseUrl": "{{resources.base_url}}",
          "kernelId": "{{kernel_id}}"
        }
    </script>
    {% set cell_count = nb.cells|length %}
    <script>
    var voila_process = function(cell_index, cell_count) {
        const loading_text = `Executing cell ${cell_index} of ${cell_count}`
        console.log(loading_text)
        app.loading_text = loading_text
        app.loadingPercentage = cell_index / cell_count * 100
    }

    </script>
    {% for cell in cell_generator(nb, kernel_id) %}
        <script>
            voila_process({{ loop.index }}, {{ cell_count }});
        </script>
    {% endfor %}

    <script>
        {% if 'jupyter-vuetify/extension' in resources.nbextensions-%}
        window.enable_nbextensions = true;
        {% endif-%}
        requirejs.config({
            baseUrl: '{{resources.base_url}}voila',
            waitSeconds: 3000,
            map: {
                '*': {
                    {% if 'jupyter-vue/extension' in resources.nbextensions-%}
                    'jupyter-vue': 'nbextensions/jupyter-vue/nodeps',
                    {% endif-%}
                    {% if 'jupyter-vuetify/extension' in resources.nbextensions-%}
                    'jupyter-vuetify': 'nbextensions/jupyter-vuetify/nodeps',
                    {% endif-%}
                },
            }
        });
        requirejs([
            {% for ext in resources.nbextensions if ext != 'jupyter-vuetify/extension' and ext != 'jupyter-vue/extension'-%}
                "{{resources.base_url}}voila/nbextensions/{{ ext }}.js",
            {% endfor %}
        ]);
        requirejs(['static/voila'], (voila) => init(voila));
    </script>
</html>

