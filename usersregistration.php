<?php
session_start();
if(isset($_SESSION["loggedin"]) != true) {
    header('Location: login.php');
    exit;
} else {
    $servername = "localhost";
    $username = $_SESSION["username"];
    $password = $_SESSION["password"];
    $dbname = "LOCKER_SYSTEM";
    $conn = mysqli_connect($servername, $username, $password, $dbname);
    $sql = "SELECT * FROM USER_REGISTRATION";
    $result = mysqli_query($conn, $sql);
}
  
?>
<html>
<header>
    <meta charseet="utf-8">
    <title>Gp3_8 Database</title>
    <link rel="stylesheet" href="bootstrap.min.css">
    <script src="bootstrap.min.js"></script>
</header>
<body>
  

    <nav class="navbar navbar-default">
        <div class="container-fluid">
            <div class="navbar-header">
                <a class="navbar-brand" href="welcome.php">Gp3_8 Locker System Database</a>
            </div>
            <ul class="nav navbar-nav">
                <li class="nav-item">
                    <a href="usersregistration.php" class="nav-link active">User registration</a>
                </li>
                <li class="nav-item">
                    <a href="historyrecord.php" class="nav-link">History record</a>
                </li>
            </ul>
        </div>
    </nav>
    <div class="container">
        <h2>Users Registration</h2>
<?php
      if (isset($_POST['submit']))   {
        $q = $conn-> real_escape_string ($_POST['q']);
        $column = $conn-> real_escape_string ($_POST['column']);
        
        if ($column == "" || ($column != "ID" &&  $column != "STUDENT_NAME" && $column != "STUDENT_ID" && $column != "UID" && $column != "REGISTRATION_TIME"))
            $column = "STUDENT_NAME";
            
        $search_sql = "SELECT * FROM USER_REGISTRATION WHERE " . $column . " LIKE '%" . $q . "%'";
        $result = mysqli_query($conn, $search_sql);

 
        }
?>
        <head>
            <form method="post" action="usersregistration.php">
                <input type="text" name="q" placeholder="Search for ......">
                <select name="column">
                    <option value="">Select Filter</option>
                    <option value="ID">User No.</option>
                    <option value="STUDENT_ID">Student ID</option>
                    <option value="STUDENT_NAME">Student Name</option>
                    <option value="UID">UID</option>
                    <option value="REGISTRATION_TIME">Registered Time</option>
                </select>
                <input type="submit" name="submit" value="Find">
            </form>
        </head>
        
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Student ID</th>
                    <th>Student Name</th>
                    <th>UID</th>
                    <th>Registration</th>
                </tr>
            </thead>
            <tbody>
                <?php
                if (mysqli_num_rows($result) > 0) {
                    while($row = mysqli_fetch_assoc($result)) {
                        echo '<tr>';
                        echo '<td>' . $row['ID'] . '</td>';
                        echo '<td>' . $row['STUDENT_ID'] . '</td>';
                        echo '<td>' . $row['STUDENT_NAME'] . '</td>';
                        echo '<td>' . $row['UID'] . '</td>';
                        echo '<td>' . $row['REGISTRATION_TIME'] . '</td>';
                        echo '</tr>';
                    }
                }
                ?>
            </tbody>
        </table>
    </div>
</body>
</html>
