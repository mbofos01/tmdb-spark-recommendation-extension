<template>
  <div class="min-vh-100 d-flex flex-column"
    style="background: linear-gradient(180deg, #374151 0%, #1f2937 100%); color: #f3f4f6;">
    <div class="container py-4">
      <h1 class="display-4 text-center mb-5">Your Movie Dashboard</h1>
      <p class="lead text-center mb-5">See your liked, unused, and recommended movies at a glance.</p>


      <h2 class="h4 mb-3"><span class="badge bg-success me-2">Your Movies</span></h2>
      <div class="row g-4 mb-5">
        <div v-for="movie in likedMovies" :key="movie.id + '-used'" class="col-12 col-sm-6 col-md-4 col-lg-3">
          <div class="card h-100 shadow-sm position-relative"
            style="background: linear-gradient(180deg, #111827, #0b0f14); color: #f3f4f6;">

            <a :href="movie.url" target="_blank" class="d-block">
              <img :src="movie.poster_path ? `https://image.tmdb.org/t/p/w300${movie.poster_path}` : ''"
                :alt="movie.title" class="card-img-top card-poster" />
            </a>

            <div class="card-body d-flex flex-column">
              <!-- Fixed-height Title -->
              <h5 class="card-title mb-2"
                style="min-height: 3.2em; max-height: 3.2em; overflow: hidden; line-height: 1.6em; white-space: normal; word-wrap: break-word;">
                {{ movie.title }}
              </h5>

              <!-- Rating -->
              <div class="card-rating mb-1" title="User rating">
                <span class="text-warning fw-bold">{{ Number(movie.vote_average).toFixed(2) }}/10</span>
                <span class="text-secondary">&nbsp;({{ movie.vote_count }} votes)</span>
              </div>

              <!-- Optional User Rating -->
              <div v-if="movie.user_rating" class="card-rating user-rating mb-2" title="Your rating">
                <span class="text-success fw-bold">Your rating: {{ Math.round(Number(movie.user_rating)) }}/10</span>
              </div>

              <!-- Confidence bar -->
              <div v-if="movie.confidence !== undefined" class="mb-2" title="Confidence score">
                <div class="progress" style="height: 18px; background: #1e293b; border-radius: 6px;">
                  <div class="progress-bar" role="progressbar"
                    :style="{ width: (movie.confidence || 0) + '%', background: 'linear-gradient(90deg, #34d399 0%, #22d3ee 100%)' }"
                    :aria-valuenow="movie.confidence || 0" aria-valuemin="0" aria-valuemax="100">
                    <span class="fw-bold text-light" style="font-size: 0.9rem; text-shadow: 0 1px 2px #000a;">
                      {{ movie.confidence }}/100
                    </span>
                  </div>
                </div>
              </div>

              <!-- Optional Unused Badge -->
              <div v-if="movie.isUnused" class="mt-2 mb-2">
                <span class="badge bg-secondary">Unused</span>
              </div>

              <!-- Push tags to bottom -->
              <div class="mt-auto">
                <div class="tags d-flex flex-wrap gap-1">
                  <span v-for="genre in (typeof movie.genres === 'string' ? movie.genres.split('|') : [])" :key="genre"
                    class="tag bg-secondary bg-opacity-25 text-secondary px-2 py-1 rounded-pill">{{ genre }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-for="movie in unusedMovies" :key="movie.id + '-unused'" class="col-12 col-sm-6 col-md-4 col-lg-3">
          <div class="card h-100 shadow-sm position-relative"
            style="background: linear-gradient(180deg, #111827, #0b0f14); color: #f3f4f6;">

            <a :href="movie.url" target="_blank" class="position-relative d-block">
              <img :src="movie.poster_path ? `https://image.tmdb.org/t/p/w300${movie.poster_path}` : ''"
                :alt="movie.title" class="card-img-top card-poster"
                style="border:none; filter: grayscale(1) brightness(0.8); opacity: 0.85;" />
              <span class="position-absolute top-0 end-0 m-2 badge bg-secondary">Unused</span>
            </a>

            <div class="card-body d-flex flex-column">
              <!-- Fixed-height Title -->
              <h5 class="card-title mb-2"
                style="min-height: 3.2em; max-height: 3.2em; overflow: hidden; line-height: 1.6em; white-space: normal; word-wrap: break-word;">
                {{ movie.title }}
              </h5>

              <!-- Rating -->
              <div class="card-rating mb-1" title="User rating">
                <span class="text-warning fw-bold">{{ Number(movie.vote_average).toFixed(2) }}/10</span>
                <span class="text-secondary">&nbsp;({{ movie.vote_count }} votes)</span>
              </div>

              <!-- Optional User Rating -->
              <div v-if="movie.user_rating" class="card-rating user-rating mb-2" title="Your rating">
                <span class="text-success fw-bold">Your rating: {{ Math.round(Number(movie.user_rating)) }}/10</span>
              </div>

              <!-- Push tags to bottom -->
              <div class="mt-auto">
                <div class="tags d-flex flex-wrap gap-1">
                  <span v-for="genre in (typeof movie.genres === 'string' ? movie.genres.split('|') : [])" :key="genre"
                    class="tag bg-secondary bg-opacity-25 text-secondary px-2 py-1 rounded-pill">{{ genre }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <h2 class="h4 mb-3"><span class="badge bg-danger me-2">Recommended Movies</span></h2>
      <div class="row g-4 mb-5">
        <div v-for="movie in recommendations" :key="movie.id + '-rec'" class="col-12 col-sm-6 col-md-4 col-lg-3">
          <div class="card h-100 shadow-sm position-relative"
            style="background: linear-gradient(180deg, #111827, #0b0f14); color: #f3f4f6;">

            <a :href="movie.url" target="_blank">
              <img :src="movie.poster_path ? `https://image.tmdb.org/t/p/w300${movie.poster_path}` : ''"
                :alt="movie.title" class="card-img-top card-poster" />
            </a>

            <div class="card-body d-flex flex-column">
              <!-- Fixed-height Title -->
              <h5 class="card-title mb-2"
                style="min-height: 3.2em; max-height: 3.2em; overflow: hidden; line-height: 1.6em; white-space: normal; word-wrap: break-word;">
                {{ movie.title }}
              </h5>

              <!-- Rating -->
              <div class="card-rating mb-2" title="User rating">
                <span class="text-warning fw-bold">{{ Number(movie.vote_average).toFixed(2) }}/10</span>
                <span class="text-secondary">({{ movie.vote_count }} votes)</span>
              </div>

              <!-- Progress / confidence bar -->
              <div v-if="movie.confidence !== undefined" class="mb-2" title="Confidence score">
                <div class="progress" style="height: 18px; background: #1e293b; border-radius: 6px;">
                  <div class="progress-bar" role="progressbar"
                    :style="{ width: (movie.confidence || 0) + '%', background: 'linear-gradient(90deg, #34d399 0%, #22d3ee 100%)' }"
                    :aria-valuenow="movie.confidence || 0" aria-valuemin="0" aria-valuemax="100">
                  </div>
                </div>
              </div>

              <!-- Push tags to bottom -->
              <div class="mt-auto">
                <div class="tags d-flex flex-wrap gap-1">
                  <span v-for="genre in (typeof movie.genres === 'string' ? movie.genres.split('|') : [])" :key="genre"
                    class="tag bg-secondary bg-opacity-25 text-secondary px-2 py-1 rounded-pill">{{ genre }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const likedMovies = ref([]);
const unusedMovies = ref([]);
const recommendations = ref([]);


onMounted(() => {
  const USER_ID_KEY = 'user_id';
  let userId = localStorage.getItem(USER_ID_KEY);
  if (!userId) {
    userId = crypto.randomUUID();
    localStorage.setItem(USER_ID_KEY, userId);
  }

  async function fetchMovies() {
    const params = new URLSearchParams(window.location.search);
    const requestToken = params.get('request_token');
    let url = `http://127.0.0.1:8000/api/get-recommendations?user_id=${userId}&top_n=20`;
    if (requestToken) url += `&request_token=${requestToken}`;
    try {
       const res = await fetch(url);
       const data = await res.json();
       if (data.error) {
          const res = await fetch("http://127.0.0.1:8000/api/request-token");
          const data = await res.json();

          const redirectUrl = encodeURIComponent(`http://127.0.0.1:3000/`);

          const tmdbUrl =
            `https://www.themoviedb.org/authenticate/${data.request_token}` +
            `?redirect_to=${redirectUrl}&request_token=${data.request_token}`;

         return;
      }
      likedMovies.value = data.used_movies || [];
      unusedMovies.value = data.unused_movies || [];
      recommendations.value = data.recommendations || [];
    } catch (err) {
      console.error('Error fetching recommendations:', err);
    }
  }
  fetchMovies();
});
</script>
