 // function pulled from W3schools and adapted
    function sortTable(n) {
      var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;

      table = document.getElementById("clip-table");
      switching = true;
      //Set the sorting direction to ascending:
      dir = "asc";
      /*Make a loop that will continue until
      no switching has been done:*/
      while (switching) {
        //start by saying: no switching is done:
        switching = false;
        rows = table.getElementsByTagName("TR");
        /*Loop through all table rows (except the
        first, which contains table headers):*/
        for (i = 1; i < (rows.length - 1); i++) {
          //start by saying there should be no switching:
          shouldSwitch = false;
          /*Get the two elements you want to compare,
          one from current row and one from the next:*/
          x = rows[i].getElementsByTagName("TD")[n];
          y = rows[i + 1].getElementsByTagName("TD")[n];
          /*check if the two rows should switch place,
          based on the direction, asc or desc:*/
          if (dir == "asc") {
            if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
              //if so, mark as a switch and break the loop:
              shouldSwitch= true;
              break;
            }
          } else if (dir == "desc") {
            if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
              //if so, mark as a switch and break the loop:
              shouldSwitch= true;
              break;
            }
          }
        }
        if (shouldSwitch) {
          /*If a switch has been marked, make the switch
          and mark that a switch has been done:*/
          rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
          switching = true;
          //Each time a switch is done, increase this count by 1:
          switchcount ++; 
        } else {
          /*If no switching has been done AND the direction is "asc",
          set the direction to "desc" and run the while loop again.*/
          if (switchcount == 0 && dir == "asc") {
            dir = "desc";
            switching = true;
          }
        }
      }
    }


    function filterTable() {
      // Declare variables 
      var input, filter, table, tr, td, i;
      input = document.getElementById("table-search");
      filter = input.value.toUpperCase();
      table = document.getElementById("clip-table");
      tr = table.getElementsByTagName("tr");
      all_rows = document.querySelector("#clip-table").rows
      // Loop through all table rows, and hide those who don't match the search query
      for (i = 1; i < all_rows.length; i++) {
          row_cells = all_rows[i].cells
          for (var j = 1; j < 8; j++){
            if (row_cells[j].textContent.toUpperCase().indexOf(filter) > -1) {
              all_rows[i].style.display = "";
            } else {
              all_rows[i].style.display = "none";
            }
          }
        } 
    }
