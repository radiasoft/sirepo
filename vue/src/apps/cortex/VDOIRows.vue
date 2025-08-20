<template>
    <tbody v-if="doi">
        <tr v-if="doi.title">
            <td><div class="lead">{{ doi.title }}</div></td>
        </tr>
        <tr>
            <td class="col-form-label">{{ doi.type }}</td>
            <td><a v-bind:href="doi.url" target="_blank">{{ doi.linkText }}</a></td>
        </tr>
        <template v-for="r in Object.keys(doi.rows)">
            <tr v-if="doi.rows[r]">
                <td class="col-form-label">{{ r }}</td>
                <td>{{ doi.rows[r] }}</td>
            </tr>
        </template>
    </tbody>
</template>

<script setup>
 import { ref, watch } from 'vue';

 const props = defineProps({
     property: Object,
     title: String,
 });

 const sourceDesc = {
     EXP: 'experiment',
     PP: 'predictive physics model',
     NOM: 'nominal (design target) value',
     ML: 'maching learning',
     DFT: 'Density Functional Theory',
 };

 const buildDOI = (doi) => {
     if (! (props.property && props.property.doi_or_url)) {
         return null;
     }
     let t, u;
     if (doi.doi_or_url.toLowerCase().startsWith('http')) {
         t = 'URL';
         u = doi.doi_or_url;
     }
     else {
         t = 'DOI';
         u = 'https://doi.org/' + doi.doi_or_url;
     }
     return {
         title: props.title,
         type: t,
         url: u,
         linkText: doi.doi_or_url,
         rows: {
             Source: source(doi.source),
             Pointer: doi.pointer,
             Comments: doi.comments,
         },
     };
 };

 const source = (value) => {
     return sourceDesc[value]
        ? `${value}, ${sourceDesc[value]}`
          : value;
 };

 const doi = ref(buildDOI(props.property));

 watch(() => props.property, () => doi.value = buildDOI(props.property));
</script>
