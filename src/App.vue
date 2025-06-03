<template>
  <div id="app">
    <ChatPanel />
    <router-view />
  </div>
</template>

<script>
import ChatPanel from './components/ChatPanel.vue'

export default {
    name: 'App',
    components: {
        ChatPanel
    }
}
</script>

<style>
@import url('https://fonts.googleapis.com/css?family=Nunito+Sans&display=swap');

#app {
  font-family: 'Nunito Sans', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

html,
body {
  overscroll-behavior-y: contain;
}
</style>
