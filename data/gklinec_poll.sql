-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Host: scancarello.iad1-mysql-e2-8a.dreamhost.com
-- Generation Time: Oct 09, 2026 at 05:55 AM
-- Server version: 8.0.41-0ubuntu0.24.04.1
-- PHP Version: 8.5.4

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `gklinec_poll`
--

-- --------------------------------------------------------

--
-- Table structure for table `poll`
--

CREATE TABLE `poll` (
  `ID_` int NOT NULL,
  `Poll_date` date DEFAULT '0000-00-00',
  `Question` varchar(255) DEFAULT NULL,
  `Text1` varchar(100) DEFAULT '0',
  `Votes1` int DEFAULT '0',
  `Text2` varchar(100) DEFAULT '0',
  `Votes2` int DEFAULT '0',
  `Text3` varchar(100) DEFAULT '0',
  `Votes3` int DEFAULT '0',
  `Text4` varchar(100) DEFAULT '0',
  `Votes4` int DEFAULT '0',
  `Text5` varchar(100) DEFAULT '0',
  `Votes5` int DEFAULT '0'
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Dumping data for table `poll`
--

INSERT INTO `poll` (`ID_`, `Poll_date`, `Question`, `Text1`, `Votes1`, `Text2`, `Votes2`, `Text3`, `Votes3`, `Text4`, `Votes4`, `Text5`, `Votes5`) VALUES
(1, '2001-07-14', 'Who was the best Godfather?', 'Marlon Brando', 2, 'Al Pacino', 4, 'Robert De Niro', 8, 'Andy Garcia', 0, '0', 0),
(2, '2001-07-25', 'Who was the best Batman?', 'Adam West', 5, 'Michael Keaton', 11, 'Val Kilmer', 6, 'George Clooney', 1, '0', 0),
(3, '2001-08-03', 'What\'s the best <i>Star Wars</i> movie so far?', 'The Phantom Menace', 2, 'A New Hope', 1, 'Empire Strikes Back', 1, 'Return of the Jedi', 4, '0', 0),
(4, '2001-08-16', 'Who was the hottest \"old school\" babe?', 'Rita Hayworth', 1, 'Audrey Hepburn', 2, 'Grace Kelly', 3, 'Marilyn Monroe', 3, 'Other', 1),
(5, '2001-08-30', 'Who\'s your favorite Baldwin?', 'Adam Baldwin', 0, 'Alec Baldwin', 6, 'Billy Baldwin', 1, 'Stephen Baldwin', 4, 'Other', 0),
(6, '2001-09-22', 'Who\'s your favorite Sheen?', 'Martin Sheen', 4, 'Charlie Sheen', 4, 'Emilio Estevez', 1, 'Sheena, Queen of the Jungle', 4, 'Other', 0),
(7, '2001-10-29', 'What\'s your favorite Kevin Smith movie?', 'Clerks', 2, 'Mallrats', 2, 'Chasing Amy', 1, 'Dogma', 2, 'Jay & Silent Bob Strike Back', 1),
(8, '2001-11-16', 'How would you most like to see this Harry Potter punk killed?', 'Hanging', 1, 'Quartering', 2, 'Guillotine', 1, 'Tar and Feather', 4, 'Other', 0),
(9, '2001-12-18', 'Who benefitted most from the Cruise/Kidman breakup?', 'Tom Cruise', 4, 'Nicole Kidman', 3, 'Penelope Cruz', 3, 'The tabloids', 9, '0', 0),
(10, '2002-04-03', 'Who\'s the toughest actress?', 'Sigourney Weaver', 2, 'Jamie Lee Curtis', 1, 'Jodie Foster', 1, 'Sandra Bullock', 1, 'Other', 1),
(11, '2002-04-25', 'How good will <i>Attack of the Clones</i> be?', 'Legitimately good', 2, 'Better than <i>Phantom Menace</i>', 3, 'About the same as <i>Phantom Menace</i>\r\n', 0, 'Worse than <i>Phantom Menace</i>', 0, '0', 0),
(12, '2002-07-15', 'What was the worst Tom Hanks movie?', 'Joe vs. the Volcano', 1, 'Sleepless in Seattle', 0, 'Bachelor Party', 2, 'Dragnet', 0, '0', 0),
(13, '2002-08-07', 'Who has become the biggest embarrassment to the values they supposedly represent?', 'Ozzy Osbourne', 4, 'Pope John Paul II', 2, 'The Rolling Stones', 1, 'George Lucas', 3, 'Bud Selig', 7),
(14, '2004-06-24', 'Which former <i>SNL</i> performer makes the best movies?', 'Will Ferrell', 46, 'Mike Myers', 37, 'Adam Sandler', 42, 'David Spade', 4, '0', 0);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `poll`
--
ALTER TABLE `poll`
  ADD PRIMARY KEY (`ID_`),
  ADD KEY `Poll_date` (`Poll_date`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `poll`
--
ALTER TABLE `poll`
  MODIFY `ID_` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
